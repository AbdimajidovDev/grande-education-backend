from unittest import mock

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import DatabaseError, transaction
from django.test import TestCase

from apps.notifications.models import Notification
from apps.notifications.realtime import user_group_name
from apps.notifications.services import NotificationService
from apps.notifications.tests.base import make_user, notification_test_settings

Type = Notification.Type
EntityType = Notification.EntityType


def _base_kwargs(**overrides):
    kwargs = {
        "type": Type.INQUIRY_ASSIGNED,
        "title": "Sarlavha",
        "message": "Xabar",
        "entity_type": EntityType.INQUIRY,
        "entity_id": "abc",
    }
    kwargs.update(overrides)
    return kwargs


class ChannelListenerMixin:
    """Foydalanuvchi group'iga tinglovchi kanal ulab, eventlarni o'qiydi."""

    def listen(self, user):
        layer = get_channel_layer()
        channel = async_to_sync(layer.new_channel)()
        async_to_sync(layer.group_add)(user_group_name(user.pk), channel)
        return channel

    def receive_all(self, channel):
        # InMemoryChannelLayer.receive bo'sh kanalda kutib qoladi, shuning
        # uchun faqat navbatda xabar bo'lsa o'qiymiz.
        layer = get_channel_layer()
        messages = []
        while self.has_messages(channel):
            messages.append(async_to_sync(layer.receive)(channel))
        return messages

    def has_messages(self, channel) -> bool:
        layer = get_channel_layer()
        queue = layer.channels.get(channel)
        return queue is not None and not queue.empty()


@notification_test_settings
class NotificationServiceTests(ChannelListenerMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.actor = make_user("svc_actor")
        cls.alice = make_user("svc_alice")
        cls.bob = make_user("svc_bob")
        cls.inactive = make_user("svc_inactive", is_active=False)

    def test_notify_creates_single_notification(self):
        notification = NotificationService.notify(
            recipient=self.alice,
            actor=self.actor,
            data={"k": "v"},
            **_base_kwargs(),
        )

        self.assertIsNotNone(notification)
        stored = Notification.objects.get(pk=notification.pk)
        self.assertEqual(stored.recipient, self.alice)
        self.assertEqual(stored.actor, self.actor)
        self.assertEqual(stored.data, {"k": "v"})
        self.assertFalse(stored.is_read)
        self.assertIsNone(stored.read_at)

    def test_notify_many_uses_single_insert_and_dedupes(self):
        with self.assertNumQueries(3):  # savepoint + INSERT + release
            created = NotificationService.notify_many(
                recipients=[self.alice, self.bob, self.alice, None],
                **_base_kwargs(),
            )

        self.assertEqual(len(created), 2)
        self.assertEqual(
            set(Notification.objects.values_list("recipient_id", flat=True)),
            {self.alice.pk, self.bob.pk},
        )

    def test_actor_and_inactive_users_are_excluded(self):
        created = NotificationService.notify_many(
            recipients=[self.actor, self.inactive, self.bob],
            actor=self.actor,
            **_base_kwargs(),
        )

        self.assertEqual([n.recipient_id for n in created], [self.bob.pk])
        self.assertIsNone(
            NotificationService.notify(
                recipient=self.actor, actor=self.actor, **_base_kwargs()
            )
        )

    def test_empty_recipients_are_safe(self):
        with self.assertNumQueries(0):
            self.assertEqual(
                NotificationService.notify_many(recipients=[], **_base_kwargs()),
                [],
            )
            self.assertEqual(
                NotificationService.notify_many(recipients=None, **_base_kwargs()),
                [],
            )

    def test_websocket_event_sent_only_after_commit(self):
        channel = self.listen(self.alice)

        with self.captureOnCommitCallbacks(execute=False) as callbacks:
            NotificationService.notify(recipient=self.alice, **_base_kwargs())

        self.assertEqual(len(callbacks), 1)
        self.assertFalse(self.has_messages(channel))

        callbacks[0]()

        messages = self.receive_all(channel)
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["type"], "notification.created")
        self.assertEqual(messages[0]["unread_count"], 1)
        self.assertEqual(messages[0]["notification"]["type"], Type.INQUIRY_ASSIGNED)

    def test_rolled_back_business_transaction_sends_nothing(self):
        channel = self.listen(self.alice)

        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            with self.assertRaises(RuntimeError):
                with transaction.atomic():
                    NotificationService.notify(recipient=self.alice, **_base_kwargs())
                    raise RuntimeError("business failure")

        self.assertEqual(callbacks, [])
        self.assertFalse(Notification.objects.exists())
        self.assertFalse(self.has_messages(channel))

    def test_db_failure_does_not_break_business_transaction(self):
        with transaction.atomic():
            other = make_user("svc_business_row")
            with mock.patch.object(
                Notification.objects,
                "bulk_create",
                side_effect=DatabaseError("boom"),
            ), self.assertLogs("apps.notifications.services.notification_service", "ERROR"):
                result = NotificationService.notify(
                    recipient=self.alice, **_base_kwargs()
                )
            # Tranzaksiya hali ishlaydi: keyingi so'rov xatosiz bajariladi.
            other.first_name = "OK"
            other.save(update_fields=["first_name"])

        self.assertIsNone(result)
        other.refresh_from_db()
        self.assertEqual(other.first_name, "OK")

    def test_channel_layer_failure_keeps_db_notification(self):
        layer = get_channel_layer()
        with mock.patch.object(
            layer, "group_send", side_effect=ConnectionError("redis down")
        ), self.assertLogs("apps.notifications.realtime", "ERROR"):
            with self.captureOnCommitCallbacks(execute=True):
                notification = NotificationService.notify(
                    recipient=self.alice, **_base_kwargs()
                )

        self.assertTrue(Notification.objects.filter(pk=notification.pk).exists())

    def test_mark_as_read_and_mark_all(self):
        first = NotificationService.notify(recipient=self.alice, **_base_kwargs())
        NotificationService.notify(recipient=self.alice, **_base_kwargs())
        NotificationService.notify(recipient=self.bob, **_base_kwargs())

        self.assertEqual(NotificationService.get_unread_count(user=self.alice), 2)

        read = NotificationService.mark_as_read(
            user=self.alice, notification_id=first.pk
        )
        self.assertTrue(read.is_read)
        self.assertIsNotNone(read.read_at)
        read_at = read.read_at

        # Idempotent: qayta chaqirish read_at'ni o'zgartirmaydi.
        again = NotificationService.mark_as_read(
            user=self.alice, notification_id=first.pk
        )
        self.assertEqual(again.read_at, read_at)

        self.assertEqual(NotificationService.mark_all_as_read(user=self.alice), 1)
        self.assertEqual(NotificationService.get_unread_count(user=self.alice), 0)
        # Bob'ning notificationiga ta'sir qilmaydi.
        self.assertEqual(NotificationService.get_unread_count(user=self.bob), 1)

    def test_mark_read_broadcasts_unread_count_for_other_tabs(self):
        notification = NotificationService.notify(recipient=self.alice, **_base_kwargs())
        channel = self.listen(self.alice)

        with self.captureOnCommitCallbacks(execute=True):
            NotificationService.mark_as_read(
                user=self.alice, notification_id=notification.pk
            )

        messages = self.receive_all(channel)
        self.assertEqual(messages[-1]["type"], "notification.unread_count")
        self.assertEqual(messages[-1]["unread_count"], 0)
