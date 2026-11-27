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

    def test_superuser_can_open_and_update_user_change_view(self):
        from django.contrib.auth.models import Group

        group = Group.objects.create(name="AdminTestRole")
        self.superuser.groups.add(group)

        self.client.force_login(self.superuser)

        change_url = f"/admin/users/user/{self.superuser.pk}/change/"
        res_get = self.client.get(change_url)
        self.assertEqual(res_get.status_code, 200)
        self.assertNotIn("groups", res_get.context["adminform"].form.fields)
        self.assertNotIn("user_permissions", res_get.context["adminform"].form.fields)
        self.assertIn("is_superuser", res_get.context["adminform"].form.fields)

        res_post = self.client.post(
            change_url,
            {
                "username": self.superuser.username,
                "first_name": "Super",
                "last_name": "Admin",
                "email": self.superuser.email,
                "phone_number": "+998901234567",
                "is_active": "on",
                "is_staff": "on",
                "is_superuser": "on",
                "last_login_0": "",
                "last_login_1": "",
                "date_joined_0": self.superuser.date_joined.strftime("%Y-%m-%d"),
                "date_joined_1": self.superuser.date_joined.strftime("%H:%M:%S"),
            },
        )
        self.assertEqual(res_post.status_code, 302)

        self.superuser.refresh_from_db()
        self.assertEqual(self.superuser.first_name, "Super")
        self.assertEqual(self.superuser.phone_number, "+998901234567")
        self.assertTrue(self.superuser.groups.filter(pk=group.pk).exists())

    def test_regular_staff_can_open_regular_user_change_view_without_is_superuser(self):
        from django.contrib.auth.models import Permission

        perms = Permission.objects.filter(
            content_type__app_label="users",
            codename__in=["view_user", "change_user", "add_user"],
        )
        self.admin_user.user_permissions.add(*perms)

        self.client.force_login(self.admin_user)

        res_regular = self.client.get(f"/admin/users/user/{self.regular_user.pk}/change/")
        self.assertEqual(res_regular.status_code, 200)
        form_fields = res_regular.context["adminform"].form.fields
        self.assertNotIn("is_superuser", form_fields)
        self.assertNotIn("groups", form_fields)
        self.assertNotIn("user_permissions", form_fields)

        res_regular_post = self.client.post(
            f"/admin/users/user/{self.regular_user.pk}/change/",
            {
                "username": self.regular_user.username,
                "first_name": "Updated",
                "last_name": "Regular",
                "email": self.regular_user.email,
                "phone_number": "+998909998877",
                "is_active": "on",
                "is_superuser": "on",
                "last_login_0": "",
                "last_login_1": "",
                "date_joined_0": self.regular_user.date_joined.strftime("%Y-%m-%d"),
                "date_joined_1": self.regular_user.date_joined.strftime("%H:%M:%S"),
            },
        )
        self.assertEqual(res_regular_post.status_code, 302)
        self.regular_user.refresh_from_db()
        self.assertEqual(self.regular_user.first_name, "Updated")
        self.assertEqual(self.regular_user.phone_number, "+998909998877")
        self.assertFalse(self.regular_user.is_superuser)

        res_add = self.client.get("/admin/users/user/add/")
        self.assertEqual(res_add.status_code, 200)

        # Superuser get_queryset dan chiqarilgani uchun change_view /admin/ ga redirect qiladi.
        res_super = self.client.get(f"/admin/users/user/{self.superuser.pk}/change/")
        self.assertEqual(res_super.status_code, 302)
        self.assertEqual(res_super.url, "/admin/")

