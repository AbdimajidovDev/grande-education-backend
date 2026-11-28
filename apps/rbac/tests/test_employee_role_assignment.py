from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from apps.rbac.services.role_service import RoleService

User = get_user_model()

IN_MEMORY_CHANNEL_LAYERS = {
    "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"},
}


def _perm(app_label, codename):
    return Permission.objects.get(content_type__app_label=app_label, codename=codename)


@override_settings(CHANNEL_LAYERS=IN_MEMORY_CHANNEL_LAYERS)
class AssignEmployeeToRolesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            username="rar_super", email="rar_super@example.com", password="Password123!"
        )

        cls.view_inquiry = _perm("inquiries", "view_inquiry")
        cls.change_inquiry = _perm("inquiries", "change_inquiry")
        cls.assign_roles = _perm("users", "assign_roles")
        cls.manage_roles = _perm("rbac", "manage_roles")

        # HR: assign_roles + view_inquiry huquqiga ega.
        cls.hr = User.objects.create_user(username="rar_hr", password="Password123!")
        hr_role = Group.objects.create(name="HR")
        hr_role.permissions.add(cls.assign_roles, cls.view_inquiry)
        cls.hr.groups.add(hr_role)

        cls.no_perm_actor = User.objects.create_user(username="rar_noperm", password="Password123!")
        cls.employee = User.objects.create_user(username="rar_employee", password="Password123!")
        cls.staff = User.objects.create_user(
            username="rar_staff", password="Password123!", is_staff=True
        )

        cls.viewer_role = Group.objects.create(name="Viewer")
        cls.viewer_role.permissions.add(cls.view_inquiry)

        cls.editor_role = Group.objects.create(name="Editor")
        cls.editor_role.permissions.add(cls.view_inquiry, cls.change_inquiry)

        cls.role_admin_role = Group.objects.create(name="Role admin")
        cls.role_admin_role.permissions.add(cls.manage_roles)

        cls.empty_role = Group.objects.create(name="Empty")

    def test_superuser_can_assign_any_role(self):
        roles = RoleService.assign_employee_to_roles(
            role_ids=[self.editor_role.pk, self.role_admin_role.pk],
            employee=self.employee,
            actor=self.superuser,
        )

        self.assertEqual({role.pk for role in roles}, {self.editor_role.pk, self.role_admin_role.pk})
        self.assertEqual(
            set(self.employee.groups.values_list("pk", flat=True)),
            {self.editor_role.pk, self.role_admin_role.pk},
        )

    def test_actor_can_assign_role_within_own_permissions(self):
        RoleService.assign_employee_to_roles(
            role_ids=[self.viewer_role.pk, self.empty_role.pk],
            employee=self.employee,
            actor=self.hr,
        )
        self.assertEqual(self.employee.groups.count(), 2)

    def test_actor_cannot_assign_role_with_permissions_they_lack(self):
        with self.assertRaises(PermissionDenied):
            RoleService.assign_employee_to_roles(
                role_ids=[self.viewer_role.pk, self.editor_role.pk],
                employee=self.employee,
                actor=self.hr,
            )
        # Atomik: viewer_role ham biriktirilmagan.
        self.assertEqual(self.employee.groups.count(), 0)

    def test_only_superuser_can_assign_role_management_role(self):
        self.hr.groups.first().permissions.add(self.manage_roles)

        with self.assertRaises(PermissionDenied):
            RoleService.assign_employee_to_roles(
                role_ids=[self.role_admin_role.pk],
                employee=self.employee,
                actor=self.hr,
            )

    def test_actor_without_assign_roles_is_denied(self):
        with self.assertRaises(PermissionDenied):
            RoleService.assign_employee_to_roles(
                role_ids=[self.empty_role.pk],
                employee=self.employee,
                actor=self.no_perm_actor,
            )

    def test_admin_accounts_and_invalid_input_are_rejected(self):
        for employee in (self.staff, self.superuser):
            with self.assertRaises(ValidationError):
                RoleService.assign_employee_to_roles(
                    role_ids=[self.viewer_role.pk],
                    employee=employee,
                    actor=self.superuser,
                )

        with self.assertRaises(ValidationError):
            RoleService.assign_employee_to_roles(
                role_ids=[self.viewer_role.pk, self.viewer_role.pk],
                employee=self.employee,
                actor=self.superuser,
            )

        with self.assertRaises(ValidationError):
            RoleService.assign_employee_to_roles(
                role_ids=[self.viewer_role.pk, 999_999],
                employee=self.employee,
                actor=self.superuser,
            )

        self.assertEqual(
            RoleService.assign_employee_to_roles(
                role_ids=[], employee=self.employee, actor=self.superuser
            ),
            [],
        )

    def test_assignment_is_idempotent(self):
        for _ in range(2):
            RoleService.assign_employee_to_roles(
                role_ids=[self.viewer_role.pk],
                employee=self.employee,
                actor=self.superuser,
            )
        self.assertEqual(self.employee.groups.count(), 1)


@override_settings(CHANNEL_LAYERS=IN_MEMORY_CHANNEL_LAYERS)
class EmployeeRoleAssignmentAPITests(TestCase):
    """Ilgari 500 qaytargan endpointlar: rol biriktirish va rol bilan xodim yaratish."""

    @classmethod
    def setUpTestData(cls):
        cls.view_inquiry = _perm("inquiries", "view_inquiry")
        cls.change_inquiry = _perm("inquiries", "change_inquiry")

        cls.hr = User.objects.create_user(username="rar_api_hr", password="Password123!")
        hr_role = Group.objects.create(name="API HR")
        hr_role.permissions.add(
            _perm("users", "assign_roles"),
            _perm("users", "add_user"),
            _perm("users", "view_user"),
            cls.view_inquiry,
        )
        cls.hr.groups.add(hr_role)

        cls.employee = User.objects.create_user(username="rar_api_emp", password="Password123!")
        cls.viewer_role = Group.objects.create(name="API Viewer")
        cls.viewer_role.permissions.add(cls.view_inquiry)
        cls.editor_role = Group.objects.create(name="API Editor")
        cls.editor_role.permissions.add(cls.view_inquiry, cls.change_inquiry)

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.hr)

    def test_assign_roles_endpoint(self):
        url = f"/api/v1/admin/employees/{self.employee.pk}/roles/"

        ok = self.client.post(url, {"role_ids": [self.viewer_role.pk]}, format="json")
        self.assertEqual(ok.status_code, status.HTTP_200_OK)
        self.assertTrue(self.employee.groups.filter(pk=self.viewer_role.pk).exists())

        forbidden = self.client.post(url, {"role_ids": [self.editor_role.pk]}, format="json")
        self.assertEqual(forbidden.status_code, status.HTTP_403_FORBIDDEN)

        missing = self.client.post(url, {"role_ids": [999_999]}, format="json")
        self.assertEqual(missing.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

    def test_create_employee_with_roles(self):
        payload = {
            "username": "rar_new_employee",
            "password": "Str0ng!Passw0rd#2026",
            "role_ids": [self.viewer_role.pk],
        }
        created = self.client.post("/api/v1/admin/employees/", payload, format="json")
        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.data)
        new_user = User.objects.get(username="rar_new_employee")
        self.assertTrue(new_user.groups.filter(pk=self.viewer_role.pk).exists())

        # Vakolatdan tashqari rol → 403 va xodim ham yaratilmaydi (bitta tranzaksiya).
        payload.update(username="rar_new_employee_2", role_ids=[self.editor_role.pk])
        denied = self.client.post("/api/v1/admin/employees/", payload, format="json")
        self.assertEqual(denied.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(User.objects.filter(username="rar_new_employee_2").exists())
