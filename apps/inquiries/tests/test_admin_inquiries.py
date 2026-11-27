import uuid

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from apps.inquiries.models import Inquiry, InquiryActivity, InquiryCategory
from apps.universities.models import University

User = get_user_model()


class AdminInquiryCreateTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            username="inq_super",
            email="inq_super@example.com",
            password="Password123!",
        )
        cls.viewer_only = cls._make_user("inq_viewer", "view_inquiry")
        cls.lead_creator = cls._make_user(
            "inq_creator",
            "add_inquiry",
            "view_inquiry",
            "view_all_inquiries",
        )
        cls.lead_manager = cls._make_user(
            "inq_manager",
            "add_inquiry",
            "assign_inquiry",
            "view_inquiry",
            "view_all_inquiries",
        )
        cls.target_agent = cls._make_user("inq_agent", "view_inquiry")

        cls.category = InquiryCategory.objects.create(slug="study-china", is_active=True)
        cls.inactive_category = InquiryCategory.objects.create(slug="archived-cat", is_active=False)
        cls.university = University.objects.create(
            status=University.Status.PUBLISHED,
            created_by=cls.superuser,
        )

    @staticmethod
    def _make_user(username, *codenames):
        user = User.objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password="Password123!",
        )
        if codenames:
            group = Group.objects.create(name=f"Group_{username}")
            perms = Permission.objects.filter(
                content_type__app_label="inquiries",
                codename__in=codenames,
            )
            group.permissions.add(*perms)
            user.groups.add(group)
        return user

    def setUp(self):
        self.client = APIClient()
        self.url = "/api/v1/admin/inquiries/"

    def test_auth_and_rbac_for_admin_create_inquiry(self):
        payload = {
            "full_name": "Dilshod Karimov",
            "phone_number": "+998901234567",
            "category": self.category.pk,
        }

        # 1. Unauthenticated -> 401
        res_anon = self.client.post(self.url, payload, format="json")
        self.assertEqual(res_anon.status_code, status.HTTP_401_UNAUTHORIZED)

        # 2. Viewer without add_inquiry -> 403
        self.client.force_authenticate(user=self.viewer_only)
        res_forbidden = self.client.post(self.url, payload, format="json")
        self.assertEqual(res_forbidden.status_code, status.HTTP_403_FORBIDDEN)

        # 3. Creator with add_inquiry -> 201
        self.client.force_authenticate(user=self.lead_creator)
        res_ok = self.client.post(self.url, payload, format="json")
        self.assertEqual(res_ok.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res_ok.data["full_name"], "Dilshod Karimov")
        self.assertEqual(res_ok.data["phone_number"], "+998901234567")
        self.assertEqual(res_ok.data["category"], "study-china")
        self.assertEqual(res_ok.data["contact_method"], Inquiry.ContactMethod.PHONE)
        self.assertEqual(res_ok.data["status"], Inquiry.Status.NEW)
        self.assertTrue(res_ok.data["consent_accepted"])
        self.assertEqual(res_ok.data["consent_version"], "admin-manual")

        inquiry = Inquiry.objects.get(pk=res_ok.data["id"])
        activity = InquiryActivity.objects.get(inquiry=inquiry)
        self.assertEqual(activity.action, InquiryActivity.Action.CREATED)
        self.assertEqual(activity.actor, self.lead_creator)

    def test_admin_create_inquiry_with_university_assignee_and_validation(self):
        # 1. Assigning to another user without assign_inquiry -> 403
        self.client.force_authenticate(user=self.lead_creator)
        res_no_assign = self.client.post(
            self.url,
            {
                "full_name": "Aziza Rahimova",
                "phone_number": "+998909876543",
                "category": self.category.pk,
                "university": str(self.university.pk),
                "assignee_id": self.target_agent.pk,
            },
            format="json",
        )
        self.assertEqual(res_no_assign.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Inquiry.objects.filter(full_name="Aziza Rahimova").exists())

        # 2. Assigning to self with add_inquiry -> 201 and university UUID serialized cleanly
        res_self = self.client.post(
            self.url,
            {
                "full_name": "Aziza Rahimova",
                "phone_number": "+998909876543",
                "category": self.category.pk,
                "university": str(self.university.pk),
                "contact_method": Inquiry.ContactMethod.TELEGRAM,
                "message": "Bakalavr granti bo'yicha",
                "note": "Call center qo'ng'irog'i",
                "assignee_id": self.lead_creator.pk,
            },
            format="json",
        )
        self.assertEqual(res_self.status_code, status.HTTP_201_CREATED)
        self.assertEqual(str(res_self.data["university_id"]), str(self.university.pk))
        self.assertEqual(res_self.data["assignee"], self.lead_creator.pk)

        # List endpoint with university_id UUID filter works too
        res_list = self.client.get(f"{self.url}?university_id={self.university.pk}")
        self.assertEqual(res_list.status_code, status.HTTP_200_OK)
        self.assertEqual(res_list.data["count"], 1)

        # 3. Manager with add_inquiry + assign_inquiry can assign to target_agent
        self.client.force_authenticate(user=self.lead_manager)
        res_mgr = self.client.post(
            self.url,
            {
                "full_name": "Sardor Alimov",
                "phone_number": "+998931112233",
                "category": self.category.pk,
                "assignee_id": self.target_agent.pk,
            },
            format="json",
        )
        self.assertEqual(res_mgr.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res_mgr.data["assignee"], self.target_agent.pk)

        # 4. Inactive category & missing required fields -> 422
        res_bad_cat = self.client.post(
            self.url,
            {
                "full_name": "Test User",
                "phone_number": "+998901111111",
                "category": self.inactive_category.pk,
            },
            format="json",
        )
        self.assertEqual(res_bad_cat.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

        res_bad_univ = self.client.post(
            self.url,
            {
                "full_name": "Test User",
                "phone_number": "+998901111111",
                "category": self.category.pk,
                "university": str(uuid.uuid4()),
            },
            format="json",
        )
        self.assertEqual(res_bad_univ.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

    @override_settings(
        CACHES={
            "default": {
                "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            }
        }
    )
    def test_public_inquiry_endpoint_still_works(self):
        res = self.client.post(
            "/api/v1/public/inquiries/",
            {
                "name": "Website User",
                "phone": "+998907778899",
                "category": self.category.pk,
                "university": str(self.university.pk),
                "contactMethod": Inquiry.ContactMethod.WHATSAPP,
                "consent": {"accepted": True, "version": "v1"},
                "locale": "uz",
                "idempotencyKey": str(uuid.uuid4()),
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["data"]["status"], Inquiry.Status.NEW)


class AdminInquiryDeleteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            username="inq_del_super",
            email="inq_del_super@example.com",
            password="Password123!",
        )
        cls.viewer_only = cls._make_user("inq_del_viewer", "view_inquiry", "view_all_inquiries")
        cls.scoped_deleter = cls._make_user("inq_del_scoped", "view_inquiry", "delete_inquiry")
        cls.other_agent = cls._make_user("inq_del_other", "view_inquiry")
        cls.full_deleter = cls._make_user(
            "inq_del_full",
            "view_inquiry",
            "view_all_inquiries",
            "delete_inquiry",
        )
        cls.category = InquiryCategory.objects.create(slug="del-cat", is_active=True)

    @staticmethod
    def _make_user(username, *codenames):
        user = User.objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password="Password123!",
        )
        if codenames:
            group = Group.objects.create(name=f"Group_{username}")
            perms = Permission.objects.filter(
                content_type__app_label="inquiries",
                codename__in=codenames,
            )
            group.permissions.add(*perms)
            user.groups.add(group)
        return user

    def _create_inquiry(self, *, full_name="Lead User", assignee=None):
        inquiry = Inquiry.objects.create(
            category=self.category,
            full_name=full_name,
            phone_number="+998901234567",
            contact_method=Inquiry.ContactMethod.PHONE,
            consent_accepted=True,
            consent_version="admin-manual",
            idempotency_key=uuid.uuid4(),
            assignee=assignee,
        )
        InquiryActivity.objects.create(
            inquiry=inquiry,
            actor=self.superuser,
            action=InquiryActivity.Action.CREATED,
            note="Test lead yaratildi.",
        )
        return inquiry

    def setUp(self):
        self.client = APIClient()

    def test_auth_and_rbac_for_delete_inquiry(self):
        inquiry = self._create_inquiry(assignee=self.scoped_deleter)
        url = f"/api/v1/admin/inquiries/{inquiry.pk}/"

        # 1. Unauthenticated -> 401
        res_anon = self.client.delete(url)
        self.assertEqual(res_anon.status_code, status.HTTP_401_UNAUTHORIZED)

        # 2. Viewer without delete_inquiry -> 403
        self.client.force_authenticate(user=self.viewer_only)
        res_forbidden = self.client.delete(url)
        self.assertEqual(res_forbidden.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Inquiry.objects.filter(pk=inquiry.pk).exists())

        # 3. Scoped deleter can delete own assigned inquiry -> 204 and cascades activities
        self.client.force_authenticate(user=self.scoped_deleter)
        res_ok = self.client.delete(url)
        self.assertEqual(res_ok.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Inquiry.objects.filter(pk=inquiry.pk).exists())
        self.assertFalse(InquiryActivity.objects.filter(inquiry_id=inquiry.pk).exists())

    def test_scoped_deleter_cannot_delete_unassigned_or_other_inquiry(self):
        other_inquiry = self._create_inquiry(full_name="Other Lead", assignee=self.other_agent)
        unassigned_inquiry = self._create_inquiry(full_name="Unassigned Lead", assignee=None)

        self.client.force_authenticate(user=self.scoped_deleter)

        res_other = self.client.delete(f"/api/v1/admin/inquiries/{other_inquiry.pk}/")
        self.assertEqual(res_other.status_code, status.HTTP_404_NOT_FOUND)

        res_unassigned = self.client.delete(f"/api/v1/admin/inquiries/{unassigned_inquiry.pk}/")
        self.assertEqual(res_unassigned.status_code, status.HTTP_404_NOT_FOUND)

        self.assertTrue(Inquiry.objects.filter(pk=other_inquiry.pk).exists())
        self.assertTrue(Inquiry.objects.filter(pk=unassigned_inquiry.pk).exists())

    def test_full_deleter_and_not_found_and_admission_set_null(self):
        from apps.admissions.models import Admission

        other_inquiry = self._create_inquiry(full_name="Linked Lead", assignee=self.other_agent)
        admission = Admission.objects.create(
            inquiry=other_inquiry,
            full_name="Linked Lead",
            phone_number="+998901234567",
        )

        self.client.force_authenticate(user=self.full_deleter)
        res_ok = self.client.delete(f"/api/v1/admin/inquiries/{other_inquiry.pk}/")
        self.assertEqual(res_ok.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Inquiry.objects.filter(pk=other_inquiry.pk).exists())

        admission.refresh_from_db()
        self.assertIsNone(admission.inquiry)

        res_missing = self.client.delete(f"/api/v1/admin/inquiries/{uuid.uuid4()}/")
        self.assertEqual(res_missing.status_code, status.HTTP_404_NOT_FOUND)
