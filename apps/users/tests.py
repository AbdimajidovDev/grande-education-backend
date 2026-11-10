from django.core.exceptions import PermissionDenied
from django.test import TestCase

# Create your tests here.

from django.contrib import admin
from django.test import RequestFactory, TestCase

from .admin import CustomUserAdmin
from .models import User


class CustomUserAdminPermissionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            username="superadmin",
            email="superadmin@example.com",
            password="TestPassword123!",
        )

        cls.admin_user = User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="TestPassword123!",
            is_staff=True,
        )

        cls.regular_user = User.objects.create_user(
            username="regular",
            email="regular@example.com",
            password="TestPassword123!",
        )

    def setUp(self):
        self.factory = RequestFactory()
        self.model_admin = CustomUserAdmin(User, admin.site)

    def test_regular_admin_cannot_see_superusers(self):
        request = self.factory.get("/admin/users/user/")
        request.user = self.admin_user

        queryset = self.model_admin.get_queryset(request)

        self.assertNotIn(self.superuser, queryset)

    def test_superadmin_can_see_other_superusers(self):
        request = self.factory.get("/admin/users/user/")
        request.user = self.superuser

        queryset = self.model_admin.get_queryset(request)

        self.assertIn(self.superuser, queryset)

    def test_regular_admin_cannot_change_superuser(self):
        request = self.factory.get("/admin/users/user/")
        request.user = self.admin_user

        self.assertFalse(
            self.model_admin.has_change_permission(
                request,
                self.superuser,
            )
        )

    def test_regular_admin_cannot_delete_superuser(self):
        request = self.factory.get("/admin/users/user/")
        request.user = self.admin_user

        self.assertFalse(
            self.model_admin.has_delete_permission(
                request,
                self.superuser,
            )
        )

    def test_last_superuser_cannot_be_demoted(self):
        request = self.factory.post("/admin/users/user/")

        # Amalni bajarayotgan Super Adminni alohida obyekt sifatida olamiz.
        request.user = User.objects.get(pk=self.superuser.pk)

        # Tahrirlanayotgan obyekt.
        self.superuser.is_superuser = False

        with self.assertRaises(PermissionDenied):
            self.model_admin.save_model(
                request,
                self.superuser,
                form=None,
                change=True,
            )

        self.superuser.refresh_from_db()
        self.assertTrue(self.superuser.is_superuser)


    def test_last_superuser_cannot_be_deleted(self):
        request = self.factory.post("/admin/users/user/")
        request.user = self.superuser

        with self.assertRaises(PermissionDenied):
            self.model_admin.delete_model(request, self.superuser)

        self.assertTrue(
            User.objects.filter(
                pk=self.superuser.pk,
                is_superuser=True,
            ).exists()
        )

    def test_bulk_delete_cannot_remove_last_superuser(self):
        request = self.factory.post("/admin/users/user/")
        request.user = User.objects.get(pk=self.superuser.pk)

        queryset = User.objects.filter(pk=self.superuser.pk)

        with self.assertRaises(PermissionDenied):
            self.model_admin.delete_queryset(request, queryset)

        self.assertTrue(
            User.objects.filter(
                pk=self.superuser.pk,
                is_superuser=True,
            ).exists()
        )

    def test_bulk_delete_can_remove_one_of_multiple_superusers(self):
        second_superuser = User.objects.create_superuser(
            username="second_superadmin",
            email="second_superadmin@example.com",
            password="TestPassword123!",
        )

        request = self.factory.post("/admin/users/user/")
        request.user = User.objects.get(pk=self.superuser.pk)

        queryset = User.objects.filter(pk=second_superuser.pk)

        self.model_admin.delete_queryset(request, queryset)

        self.assertFalse(
            User.objects.filter(pk=second_superuser.pk).exists()
        )
        self.assertTrue(
            User.objects.filter(
                pk=self.superuser.pk,
                is_superuser=True,
            ).exists()
        )

