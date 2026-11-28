"""Redis / channel layer ishlamay qolganda biznes amali va API javobi saqlanishi.

TransactionTestCase: on_commit callback'lari haqiqiy commitdan keyin, xuddi
production'dagidek ishlaydi (captureOnCommitCallbacks emas).
"""

import asyncio
import time
import uuid
from unittest import mock

from channels.layers import get_channel_layer
from django.db import DatabaseError
from django.test import TransactionTestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from apps.inquiries.models import Inquiry, InquiryCategory
from apps.notifications.models import Notification
from apps.notifications.tests.base import IN_MEMORY_CHANNEL_LAYERS, make_user

# Hech kim tinglamayotgan port — haqiqiy "Redis o'chgan" holati (connection refused).
DEAD_REDIS_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": ["redis://127.0.0.1:6399/3"]},
    },
}

REALTIME_LOGGER = "apps.notifications.realtime"


class RealtimeFailureResilienceTests(TransactionTestCase):
    def setUp(self):
        self.manager = make_user(
            "res_manager",
            "inquiries.view_inquiry",
            "inquiries.view_all_inquiries",
            "inquiries.assign_inquiry",
        )
        self.agent = make_user("res_agent", "inquiries.view_inquiry")
        category = InquiryCategory.objects.create(slug="res-cat", is_active=True)
        self.inquiry = Inquiry.objects.create(
            category=category,
            full_name="Mijoz",
            phone_number="+998900000000",
            contact_method=Inquiry.ContactMethod.PHONE,
            consent_accepted=True,
            consent_version="v1",
            idempotency_key=uuid.uuid4(),
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.manager)
        self.url = f"/api/v1/admin/inquiries/{self.inquiry.pk}/assign/"

    def _assign(self):
        return self.client.patch(self.url, {"assignee_id": self.agent.pk}, format="json")

    def _assert_business_saved(self, response):
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.inquiry.refresh_from_db()
        self.assertEqual(self.inquiry.assignee_id, self.agent.pk)
        # Notification DB'da saqlangan — xodim uni REST orqali oladi.
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.agent,
                type=Notification.Type.INQUIRY_ASSIGNED,
            ).exists()
        )

    @override_settings(CHANNEL_LAYERS=DEAD_REDIS_LAYERS)
    def test_redis_down_keeps_transaction_and_returns_200(self):
        with self.assertLogs(REALTIME_LOGGER, "ERROR") as logs:
            response = self._assign()

        self._assert_business_saved(response)
        self.assertIn("Real-time event yuborilmadi", "\n".join(logs.output))

    @override_settings(CHANNEL_LAYERS=DEAD_REDIS_LAYERS)
    def test_redis_down_on_mark_read_returns_200(self):
        notification = Notification.objects.create(
            recipient=self.manager,
            type=Notification.Type.INQUIRY_ASSIGNED,
            title="T",
            entity_type=Notification.EntityType.INQUIRY,
            entity_id="1",
        )

        with self.assertLogs(REALTIME_LOGGER, "ERROR"):
            response = self.client.patch(
                f"/api/v1/admin/notifications/{notification.pk}/read/"
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)

    @override_settings(CHANNEL_LAYERS=IN_MEMORY_CHANNEL_LAYERS)
    def test_error_inside_callback_after_commit_does_not_cause_500(self):
        # Commitdan keyingi unread count so'rovi yiqilsa ham javob 200.
        with mock.patch(
            "apps.notifications.services.notification_service.get_unread_counts",
            side_effect=DatabaseError("db gone after commit"),
        ), self.assertLogs(REALTIME_LOGGER, "ERROR") as logs:
            response = self._assign()

        self._assert_business_saved(response)
        self.assertIn("Real-time callback bajarilmadi", "\n".join(logs.output))

    @override_settings(
        CHANNEL_LAYERS={"default": {"BACKEND": "not.a.real.ChannelLayer"}},
    )
    def test_misconfigured_channel_layer_does_not_cause_500(self):
        with self.assertLogs(REALTIME_LOGGER, "ERROR"):
            response = self._assign()

        self._assert_business_saved(response)

    @override_settings(
        CHANNEL_LAYERS=IN_MEMORY_CHANNEL_LAYERS,
        NOTIFICATIONS_WS_SEND_TIMEOUT=0.2,
    )
    def test_hanging_redis_is_cut_by_timeout(self):
        async def hanging_group_send(*args, **kwargs):
            await asyncio.sleep(10)

        layer = get_channel_layer()
        with mock.patch.object(layer, "group_send", hanging_group_send), \
                self.assertLogs(REALTIME_LOGGER, "ERROR"):
            started = time.monotonic()
            response = self._assign()
            elapsed = time.monotonic() - started

        self._assert_business_saved(response)
        self.assertLess(elapsed, 3, "API javobi Redis timeout'ini kutib qoldi")
