import uuid

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.notifications.models import Notification
from apps.notifications.tests.base import make_user, notification_test_settings

BASE_URL = "/api/v1/admin/notifications/"


def _create(recipient, *, is_read=False, title="T"):
    return Notification.objects.create(
        recipient=recipient,
        type=Notification.Type.INQUIRY_ASSIGNED,
        title=title,
        message="M",
        entity_type=Notification.EntityType.INQUIRY,
        entity_id=str(uuid.uuid4()),
        is_read=is_read,
    )


@notification_test_settings
class NotificationAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alice = make_user("api_alice")
        cls.bob = make_user("api_bob")

    def setUp(self):
        self.client = APIClient()

    def test_requires_authentication(self):
        for method, url in (
            ("get", BASE_URL),
            ("get", f"{BASE_URL}unread-count/"),
            ("post", f"{BASE_URL}read-all/"),
            ("patch", f"{BASE_URL}{uuid.uuid4()}/read/"),
        ):
            response = getattr(self.client, method)(url)
            self.assertEqual(
                response.status_code, status.HTTP_401_UNAUTHORIZED, url
            )

    def test_inactive_user_is_rejected(self):
        inactive = make_user("api_inactive", is_active=False)
        self.client.force_authenticate(user=inactive)
        response = self.client.get(BASE_URL)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_returns_only_own_notifications_newest_first(self):
        older = _create(self.alice, title="older")
        newer = _create(self.alice, title="newer")
        _create(self.bob, title="bob-only")

        self.client.force_authenticate(user=self.alice)
        response = self.client.get(BASE_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)
        ids = [item["id"] for item in response.data["results"]]
        self.assertEqual(ids, [str(newer.pk), str(older.pk)])
        self.assertEqual(
            set(response.data["results"][0].keys()),
            {
                "id", "type", "title", "message", "entity_type", "entity_id",
                "data", "is_read", "read_at", "created_at",
            },
        )

    def test_is_read_filter_and_pagination(self):
        for _ in range(3):
            _create(self.alice)
        _create(self.alice, is_read=True)

        self.client.force_authenticate(user=self.alice)

        unread = self.client.get(BASE_URL, {"is_read": "false"})
        self.assertEqual(unread.data["count"], 3)

        read = self.client.get(BASE_URL, {"is_read": "true"})
        self.assertEqual(read.data["count"], 1)

        page = self.client.get(BASE_URL, {"page_size": 2})
        self.assertEqual(page.data["count"], 4)
        self.assertEqual(len(page.data["results"]), 2)
        self.assertIsNotNone(page.data["next"])

        invalid = self.client.get(BASE_URL, {"is_read": "maybe"})
        self.assertEqual(invalid.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

    def test_list_query_count_is_constant(self):
        for _ in range(5):
            _create(self.alice)
        self.client.force_authenticate(user=self.alice)

        # COUNT + SELECT; foydalanuvchi force_authenticate orqali beriladi.
        with self.assertNumQueries(2):
            self.client.get(BASE_URL)

    def test_unread_count(self):
        _create(self.alice)
        _create(self.alice)
        _create(self.alice, is_read=True)
        _create(self.bob)

        self.client.force_authenticate(user=self.alice)
        response = self.client.get(f"{BASE_URL}unread-count/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"unread_count": 2})

    def test_mark_read(self):
        notification = _create(self.alice)
        self.client.force_authenticate(user=self.alice)

        response = self.client.patch(f"{BASE_URL}{notification.pk}/read/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["is_read"])
        self.assertIsNotNone(response.data["read_at"])
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)

    def test_cannot_read_or_mark_other_users_notification(self):
        bobs = _create(self.bob, title="secret")
        self.client.force_authenticate(user=self.alice)

        response = self.client.patch(f"{BASE_URL}{bobs.pk}/read/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertNotIn("secret", str(response.data))
        bobs.refresh_from_db()
        self.assertFalse(bobs.is_read)

        missing = self.client.patch(f"{BASE_URL}{uuid.uuid4()}/read/")
        self.assertEqual(missing.status_code, status.HTTP_404_NOT_FOUND)
        # Ikkala javob bir xil: begona ID mavjudligi oshkor qilinmaydi.
        self.assertEqual(response.data["error"], missing.data["error"])

    def test_read_all(self):
        _create(self.alice)
        _create(self.alice)
        bobs = _create(self.bob)

        self.client.force_authenticate(user=self.alice)
        response = self.client.post(f"{BASE_URL}read-all/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"updated_count": 2, "unread_count": 0})
        bobs.refresh_from_db()
        self.assertFalse(bobs.is_read)
