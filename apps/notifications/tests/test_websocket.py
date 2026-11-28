from datetime import timedelta

from channels.db import database_sync_to_async
from channels.routing import URLRouter
from channels.security.websocket import OriginValidator
from channels.testing import WebsocketCommunicator
from django.db import transaction
from django.test import TransactionTestCase
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from apps.notifications.auth import JWTCookieAuthMiddleware
from apps.notifications.consumers import (
    CLOSE_SESSION_TERMINATED,
    CLOSE_UNAUTHENTICATED,
)
from apps.notifications.models import Notification
from apps.notifications.realtime import (
    notify_permissions_changed,
    send_to_user,
    terminate_user_sessions,
)
from apps.notifications.routing import websocket_urlpatterns
from apps.notifications.services import NotificationService
from apps.notifications.tests.base import (
    ALLOWED_ORIGIN,
    make_user,
    notification_test_settings,
)

WS_PATH = "/ws/notifications/"


def build_application():
    # core.asgi bilan bir xil stack; origin ro'yxati testga xos.
    return OriginValidator(
        JWTCookieAuthMiddleware(URLRouter(websocket_urlpatterns)),
        [ALLOWED_ORIGIN],
    )


def access_token_for(user, *, lifetime: timedelta | None = None) -> str:
    token = AccessToken.for_user(user)
    if lifetime is not None:
        token.set_exp(lifetime=lifetime)
    return str(token)


@notification_test_settings
class NotificationWebSocketTests(TransactionTestCase):
    """TransactionTestCase: channels'ning database_sync_to_async har chaqiruvda
    close_old_connections() bajaradi, bu TestCase tranzaksiyasini PostgreSQL'da
    yopib qo'yadi. Bu yerda on_commit ham haqiqiy commitdan keyin ishlaydi.
    """

    def setUp(self):
        self.alice = make_user("ws_alice")
        self.bob = make_user("ws_bob")
        self.inactive = make_user("ws_inactive", is_active=False)
        Notification.objects.create(
            recipient=self.alice,
            type=Notification.Type.INQUIRY_ASSIGNED,
            title="Old",
            entity_type=Notification.EntityType.INQUIRY,
            entity_id="1",
        )

    def communicator(self, *, token: str | None = None, origin: str = ALLOWED_ORIGIN, app=None):
        headers = []
        if origin is not None:
            headers.append((b"origin", origin.encode()))
        if token is not None:
            headers.append((b"cookie", f"access_token={token}; other=1".encode()))
        return WebsocketCommunicator(app or build_application(), WS_PATH, headers=headers)

    async def connect_ok(self, user):
        communicator = self.communicator(token=access_token_for(user))
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        first = await communicator.receive_json_from()
        self.assertEqual(first["type"], "unread_count")
        return communicator, first

    async def assert_closed_with(self, communicator, code):
        connected, _ = await communicator.connect()
        self.assertTrue(connected)  # accept + close (brauzer kodni ko'rishi uchun)
        output = await communicator.receive_output()
        self.assertEqual(output["type"], "websocket.close")
        self.assertEqual(output["code"], code)
        await communicator.disconnect()

    # --- autentifikatsiya ------------------------------------------------

    async def test_valid_cookie_jwt_connects_and_gets_unread_count(self):
        communicator, first = await self.connect_ok(self.alice)
        self.assertEqual(first["unread_count"], 1)

        await communicator.send_json_to({"type": "ping"})
        self.assertEqual(await communicator.receive_json_from(), {"type": "pong"})
        await communicator.disconnect()

    async def test_missing_token_is_rejected(self):
        await self.assert_closed_with(self.communicator(), CLOSE_UNAUTHENTICATED)

    async def test_invalid_token_is_rejected(self):
        await self.assert_closed_with(
            self.communicator(token="not-a-jwt"), CLOSE_UNAUTHENTICATED
        )

    async def test_expired_token_is_rejected(self):
        token = access_token_for(self.alice, lifetime=-timedelta(minutes=1))
        await self.assert_closed_with(self.communicator(token=token), CLOSE_UNAUTHENTICATED)

    async def test_refresh_token_cannot_be_used_as_access(self):
        # for_user OutstandingToken yozuvini yaratadi (token_blacklist).
        refresh = await database_sync_to_async(
            lambda: str(RefreshToken.for_user(self.alice))
        )()
        await self.assert_closed_with(self.communicator(token=refresh), CLOSE_UNAUTHENTICATED)

    async def test_inactive_user_is_rejected(self):
        token = access_token_for(self.inactive)
        await self.assert_closed_with(self.communicator(token=token), CLOSE_UNAUTHENTICATED)

    async def test_foreign_or_missing_origin_is_rejected(self):
        token = access_token_for(self.alice)
        for origin in ("https://evil.example.com", None):
            communicator = self.communicator(token=token, origin=origin)
            connected, _ = await communicator.connect()
            self.assertFalse(connected, origin)
            await communicator.disconnect()

    async def test_connection_closes_when_token_expires(self):
        token = access_token_for(self.alice, lifetime=timedelta(seconds=1))
        communicator = self.communicator(token=token)
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        await communicator.receive_json_from()  # unread_count

        self.assertEqual(
            await communicator.receive_json_from(timeout=3),
            {"type": "token_expired"},
        )
        output = await communicator.receive_output(timeout=1)
        self.assertEqual(output["type"], "websocket.close")
        self.assertEqual(output["code"], CLOSE_UNAUTHENTICATED)
        await communicator.disconnect()

    # --- group izolyatsiyasi va yetkazish --------------------------------

    async def test_user_does_not_receive_other_users_events(self):
        alice_ws, _ = await self.connect_ok(self.alice)

        await database_sync_to_async(send_to_user)(
            user_id=self.bob.pk,
            event={"type": "permissions.changed"},
        )

        self.assertTrue(await alice_ws.receive_nothing(timeout=0.3))
        await alice_ws.disconnect()

    async def test_client_cannot_subscribe_to_another_group(self):
        alice_ws, _ = await self.connect_ok(self.alice)

        await alice_ws.send_json_to({"type": "subscribe", "group": f"user_{self.bob.pk}"})
        error = await alice_ws.receive_json_from()
        self.assertEqual(error["type"], "error")
        self.assertEqual(error["code"], "unsupported_event")

        await database_sync_to_async(send_to_user)(
            user_id=self.bob.pk,
            event={"type": "permissions.changed"},
        )
        self.assertTrue(await alice_ws.receive_nothing(timeout=0.3))
        await alice_ws.disconnect()

    async def test_notification_is_delivered_after_commit(self):
        bob_ws, _ = await self.connect_ok(self.bob)

        @database_sync_to_async
        def create():
            with transaction.atomic():
                return NotificationService.notify(
                    recipient=self.bob,
                    actor=self.alice,
                    type=Notification.Type.INQUIRY_ASSIGNED,
                    title="Yangi ariza biriktirildi",
                    message="Sizga yangi ariza biriktirildi",
                    entity_type=Notification.EntityType.INQUIRY,
                    entity_id="123",
                )

        notification = await create()
        event = await bob_ws.receive_json_from()

        self.assertEqual(event["type"], "notification.created")
        self.assertEqual(event["unread_count"], 1)
        self.assertEqual(event["data"]["id"], str(notification.pk))
        self.assertEqual(event["data"]["entity_id"], "123")
        self.assertFalse(event["data"]["is_read"])
        await bob_ws.disconnect()

    async def test_multiple_connections_of_same_user_receive_event(self):
        tab1, _ = await self.connect_ok(self.bob)
        tab2, _ = await self.connect_ok(self.bob)

        @database_sync_to_async
        def change():
            with transaction.atomic():
                notify_permissions_changed(user_ids=[self.bob.pk])

        await change()

        self.assertEqual(await tab1.receive_json_from(), {"type": "permissions_changed"})
        self.assertEqual(await tab2.receive_json_from(), {"type": "permissions_changed"})
        await tab1.disconnect()
        await tab2.disconnect()

    async def test_session_terminate_closes_connection(self):
        bob_ws, _ = await self.connect_ok(self.bob)

        @database_sync_to_async
        def terminate():
            with transaction.atomic():
                terminate_user_sessions(user_id=self.bob.pk)

        await terminate()

        self.assertEqual(
            await bob_ws.receive_json_from(), {"type": "session_terminated"}
        )
        output = await bob_ws.receive_output()
        self.assertEqual(output["type"], "websocket.close")
        self.assertEqual(output["code"], CLOSE_SESSION_TERMINATED)
        await bob_ws.disconnect()

    async def test_project_asgi_application_routes_websocket(self):
        from core.asgi import application

        communicator = self.communicator(
            token=access_token_for(self.alice),
            app=application,
        )
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        self.assertEqual((await communicator.receive_json_from())["type"], "unread_count")
        await communicator.disconnect()
