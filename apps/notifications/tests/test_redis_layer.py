"""Haqiqiy Redis channel layer bilan integratsiya (Redis bo'lmasa skip)."""

import uuid
from unittest import skipUnless

import redis
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from django.conf import settings
from django.db import transaction
from django.test import TransactionTestCase, override_settings
from rest_framework_simplejwt.tokens import AccessToken

from apps.notifications.models import Notification
from apps.notifications.services import NotificationService
from apps.notifications.tests.base import ALLOWED_ORIGIN, make_user
from apps.notifications.tests.test_websocket import WS_PATH, build_application

REDIS_URL = settings.CHANNEL_LAYERS["default"]["CONFIG"]["hosts"][0]


def _redis_available() -> bool:
    try:
        return bool(redis.Redis.from_url(REDIS_URL, socket_connect_timeout=1).ping())
    except redis.RedisError:
        return False


@skipUnless(_redis_available(), "Redis mavjud emas")
@override_settings(
    WEBSOCKET_ALLOWED_ORIGINS=[ALLOWED_ORIGIN],
    CHANNEL_LAYERS={
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {
                "hosts": [REDIS_URL],
                # Har test ishga tushishida alohida prefix — real kalitlar bilan
                # to'qnashmaydi, 60 soniyada o'zi o'chadi.
                "prefix": f"cu_grande:test:{uuid.uuid4().hex[:8]}",
                "expiry": 60,
            },
        },
    },
)
class RedisChannelLayerIntegrationTests(TransactionTestCase):
    def setUp(self):
        self.user = make_user("redis_user")
        self.actor = make_user("redis_actor")

    async def test_notification_delivered_through_redis(self):
        communicator = WebsocketCommunicator(
            build_application(),
            WS_PATH,
            headers=[
                (b"origin", ALLOWED_ORIGIN.encode()),
                (b"cookie", f"access_token={AccessToken.for_user(self.user)}".encode()),
            ],
        )
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        self.assertEqual((await communicator.receive_json_from())["type"], "unread_count")

        @database_sync_to_async
        def create():
            with transaction.atomic():
                return NotificationService.notify(
                    recipient=self.user,
                    actor=self.actor,
                    type=Notification.Type.REVISION_REJECTED,
                    title="Revision rad etildi",
                    message="Sabab: test",
                    entity_type=Notification.EntityType.FAQ_REVISION,
                    entity_id=uuid.uuid4(),
                    data={"reason": "test", "revision_number": 2},
                )

        notification = await create()
        event = await communicator.receive_json_from(timeout=3)

        self.assertEqual(event["type"], "notification.created")
        self.assertEqual(event["data"]["id"], str(notification.pk))
        self.assertEqual(event["data"]["data"], {"reason": "test", "revision_number": 2})
        self.assertEqual(event["unread_count"], 1)
        await communicator.disconnect()
