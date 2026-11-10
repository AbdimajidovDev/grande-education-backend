
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.exceptions import ValidationError, PermissionDenied
from django.test import TestCase

from apps.rbac.services.role_service import RoleService

User = get_user_model()


class CreateRoleTests(TestCase):

    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username="superadmin",
            email="superadmin@example.com",
            password="test-password-123",
        )

        self.manager = User.objects.create_user(
            username="role_manager",
            password="test-password-123",
        )

        self.manager_permission = Permission.objects.get(
            content_type__app_label="rbac",
            codename="manage_roles",
        )

        self.manager.user_permissions.add(self.manager_permission)

        self.regular_user = User.objects.create_user(
            username="regular_user",
            password="test-password-123",
        )

    def test_superuser_can_create_role(self):
        role = RoleService.create_role(
            name="Content Editor",
            actor=self.superuser,
        )

        self.assertEqual(role.name, "Content Editor")
        self.assertTrue(Group.objects.filter(pk=role.pk).exists())

    def test_role_manager_can_create_role(self):
        role = RoleService.create_role(
            name="Admission Manager",
            actor=self.manager,
        )

        self.assertEqual(role.name, "Admission Manager")

    def test_regular_user_cannot_create_role(self):
        with self.assertRaises(PermissionDenied):
            RoleService.create_role(
                name="Analyst",
                actor=self.regular_user,
            )

    def test_empty_role_name_is_rejected(self):
        with self.assertRaises(ValidationError):
            RoleService.create_role(
                name="   ",
                actor=self.superuser,
            )

    def test_duplicate_role_name_is_rejected(self):
        Group.objects.create(name="Content Editor")

        with self.assertRaises(ValidationError):
            RoleService.create_role(
                name="content editor",
                actor=self.superuser,
            )



class UpdateRoleTests(TestCase):

    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username="superadmin",
            email="superadmin@example.com",
            password="test-password-123",
        )

        self.manager = User.objects.create_user(
            username="role_manager",
            password="test-password-123",
        )

        self.manager_permission = Permission.objects.get(
            content_type__app_label="rbac",
            codename="manage_roles",
        )
        self.manager.user_permissions.add(self.manager_permission)

        self.role = Group.objects.create(name="Content Editor")

    def test_superuser_can_update_role(self):
        updated_role = RoleService.update_role(
            role_id=self.role.pk,
            name="Senior Content Editor",
            actor=self.superuser,
        )

        self.assertEqual(updated_role.name, "Senior Content Editor")

    def test_role_manager_can_update_role(self):
        updated_role = RoleService.update_role(
            role_id=self.role.pk,
            name="Admission Manager",
            actor=self.manager,
        )

        self.assertEqual(updated_role.name, "Admission Manager")

    def test_duplicate_role_name_is_rejected(self):
        Group.objects.create(name="Admission Manager")

        with self.assertRaises(ValidationError):
            RoleService.update_role(
                role_id=self.role.pk,
                name="admission manager",
                actor=self.superuser,
            )

    def test_empty_role_name_is_rejected(self):
        with self.assertRaises(ValidationError):
            RoleService.update_role(
                role_id=self.role.pk,
                name="   ",
                actor=self.superuser,
            )

    def test_nonexistent_role_cannot_be_updated(self):
        with self.assertRaises(ValidationError):
            RoleService.update_role(
                role_id=999999,
                name="New Role",
                actor=self.superuser,
            )

    def test_regular_user_cannot_update_role(self):
        regular_user = User.objects.create_user(
            username="regular_user",
            password="test-password-123",
        )

        with self.assertRaises(PermissionDenied):
            RoleService.update_role(
                role_id=self.role.pk,
                name="New Role",
                actor=regular_user,
            )



class DeleteRoleTests(TestCase):

    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username="superadmin",
            email="superadmin@example.com",
            password="test-password-123",
        )

        self.manager = User.objects.create_user(
            username="role_manager",
            password="test-password-123",
        )

        self.manager_permission = Permission.objects.get(
            content_type__app_label="rbac",
            codename="manage_roles",
        )
        self.manager.user_permissions.add(self.manager_permission)

        self.role = Group.objects.create(name="Content Editor")

    def test_superuser_can_delete_empty_role(self):
        role_id = self.role.pk

        RoleService.delete_role(
            role_id=role_id,
            actor=self.superuser,
        )

        self.assertFalse(Group.objects.filter(pk=role_id).exists())

    def test_role_manager_can_delete_empty_role(self):
        role_id = self.role.pk

        RoleService.delete_role(
            role_id=role_id,
            actor=self.manager,
        )

        self.assertFalse(Group.objects.filter(pk=role_id).exists())

    def test_role_with_assigned_users_cannot_be_deleted(self):
        user = User.objects.create_user(
            username="regular_user",
            password="test-password-123",
        )
        self.role.user_set.add(user)

        with self.assertRaises(ValidationError):
            RoleService.delete_role(
                role_id=self.role.pk,
                actor=self.superuser,
            )

        self.assertTrue(
            Group.objects.filter(pk=self.role.pk).exists()
        )

    def test_nonexistent_role_cannot_be_deleted(self):
        with self.assertRaises(ValidationError):
            RoleService.delete_role(
                role_id=999999,
                actor=self.superuser,
            )

    def test_regular_user_cannot_delete_role(self):
        regular_user = User.objects.create_user(
            username="unauthorized_user",
            password="test-password-123",
        )

        with self.assertRaises(PermissionDenied):
            RoleService.delete_role(
                role_id=self.role.pk,
                actor=regular_user,
            )

        self.assertTrue(
            Group.objects.filter(pk=self.role.pk).exists()
        )



class PermissionManagementTests(TestCase):

    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username="superadmin",
            email="superadmin@example.com",
            password="test-password-123",
        )

        self.manager = User.objects.create_user(
            username="role_manager",
            password="test-password-123",
        )

        self.role = Group.objects.create(name="Content Editor")

        self.manage_roles_permission = Permission.objects.get(
            content_type__app_label="rbac",
            codename="manage_roles",
        )

        self.view_user_permission = Permission.objects.get(
            content_type__app_label="users",
            codename="view_user",
        )

        self.change_user_permission = Permission.objects.get(
            content_type__app_label="users",
            codename="change_user",
        )

        self.manager.user_permissions.add(
            self.manage_roles_permission,
            self.view_user_permission,
        )

    def test_superuser_can_assign_any_permission(self):
        RoleService.assign_permissions(
            role_id=self.role.pk,
            permission_ids=[self.change_user_permission.pk],
            actor=self.superuser,
        )

        self.assertTrue(
            self.role.permissions.filter(
                pk=self.change_user_permission.pk
            ).exists()
        )

    def test_manager_can_assign_permission_they_possess(self):
        RoleService.assign_permissions(
            role_id=self.role.pk,
            permission_ids=[self.view_user_permission.pk],
            actor=self.manager,
        )

        self.assertTrue(
            self.role.permissions.filter(
                pk=self.view_user_permission.pk
            ).exists()
        )

    def test_manager_cannot_assign_permission_they_do_not_possess(self):
        with self.assertRaises(PermissionDenied):
            RoleService.assign_permissions(
                role_id=self.role.pk,
                permission_ids=[self.change_user_permission.pk],
                actor=self.manager,
            )

    def test_manager_cannot_assign_manage_roles_permission(self):
        with self.assertRaises(PermissionDenied):
            RoleService.assign_permissions(
                role_id=self.role.pk,
                permission_ids=[self.manage_roles_permission.pk],
                actor=self.manager,
            )

    def test_nonexistent_permission_cannot_be_assigned(self):
        with self.assertRaises(ValidationError):
            RoleService.assign_permissions(
                role_id=self.role.pk,
                permission_ids=[999999],
                actor=self.superuser,
            )

    def test_superuser_can_remove_any_permission(self):
        self.role.permissions.add(self.change_user_permission)

        RoleService.remove_permissions(
            role_id=self.role.pk,
            permission_ids=[self.change_user_permission.pk],
            actor=self.superuser,
        )

        self.assertFalse(
            self.role.permissions.filter(
                pk=self.change_user_permission.pk
            ).exists()
        )

    def test_manager_can_remove_permission_they_possess(self):
        self.role.permissions.add(self.view_user_permission)

        RoleService.remove_permissions(
            role_id=self.role.pk,
            permission_ids=[self.view_user_permission.pk],
            actor=self.manager,
        )

        self.assertFalse(
            self.role.permissions.filter(
                pk=self.view_user_permission.pk
            ).exists()
        )

    def test_manager_cannot_remove_permission_they_do_not_possess(self):
        self.role.permissions.add(self.change_user_permission)

        with self.assertRaises(PermissionDenied):
            RoleService.remove_permissions(
                role_id=self.role.pk,
                permission_ids=[self.change_user_permission.pk],
                actor=self.manager,
            )

    def test_manager_cannot_remove_manage_roles_permission(self):
        self.role.permissions.add(self.manage_roles_permission)

        with self.assertRaises(PermissionDenied):
            RoleService.remove_permissions(
                role_id=self.role.pk,
                permission_ids=[self.manage_roles_permission.pk],
                actor=self.manager,
            )

    def test_nonexistent_permission_cannot_be_removed(self):
        with self.assertRaises(ValidationError):
            RoleService.remove_permissions(
                role_id=self.role.pk,
                permission_ids=[999999],
                actor=self.superuser,
            )



class UserRoleAssignmentTests(TestCase):

    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username="superadmin",
            email="superadmin@example.com",
            password="test-password-123",
        )

        self.manager = User.objects.create_user(
            username="role_manager",
            password="test-password-123",
        )

        self.role = Group.objects.create(name="Content Editor")

        self.user1 = User.objects.create_user(
            username="user1",
            password="test-password-123",
        )

        self.user2 = User.objects.create_user(
            username="user2",
            password="test-password-123",
        )

        self.manage_roles_permission = Permission.objects.get(
            content_type__app_label="rbac",
            codename="manage_roles",
        )

        self.manager.user_permissions.add(self.manage_roles_permission)

    def test_superuser_can_assign_user_to_role(self):
        role, affected_ids = RoleService.assign_users_to_role(
            role_id=self.role.pk,
            user_ids=[self.user1.pk],
            actor=self.superuser,
        )

        self.assertEqual(role.pk, self.role.pk)
        self.assertEqual(affected_ids, [self.user1.pk])
        self.assertTrue(self.role.user_set.filter(pk=self.user1.pk).exists())

    def test_role_manager_can_assign_user_to_role(self):
        _, affected_ids = RoleService.assign_users_to_role(
            role_id=self.role.pk,
            user_ids=[self.user1.pk],
            actor=self.manager,
        )

        self.assertEqual(affected_ids, [self.user1.pk])

    def test_multiple_users_can_be_assigned(self):
        _, affected_ids = RoleService.assign_users_to_role(
            role_id=self.role.pk,
            user_ids=[self.user1.pk, self.user2.pk],
            actor=self.superuser,
        )

        self.assertCountEqual(
            affected_ids,
            [self.user1.pk, self.user2.pk],
        )

    def test_duplicate_assignment_does_not_create_duplicate_relation(self):
        RoleService.assign_users_to_role(
            role_id=self.role.pk,
            user_ids=[self.user1.pk],
            actor=self.superuser,
        )

        _, affected_ids = RoleService.assign_users_to_role(
            role_id=self.role.pk,
            user_ids=[self.user1.pk],
            actor=self.superuser,
        )

        self.assertEqual(affected_ids, [])
        self.assertEqual(self.role.user_set.count(), 1)

    def test_superuser_cannot_be_assigned_to_regular_role(self):
        with self.assertRaises(ValidationError):
            RoleService.assign_users_to_role(
                role_id=self.role.pk,
                user_ids=[self.superuser.pk],
                actor=self.superuser,
            )

        self.assertFalse(
            self.role.user_set.filter(pk=self.superuser.pk).exists()
        )

    def test_nonexistent_user_cannot_be_assigned(self):
        with self.assertRaises(ValidationError):
            RoleService.assign_users_to_role(
                role_id=self.role.pk,
                user_ids=[999999],
                actor=self.superuser,
            )

    def test_superuser_can_remove_assigned_user(self):
        self.role.user_set.add(self.user1)

        _, affected_ids = RoleService.remove_users_from_role(
            role_id=self.role.pk,
            user_ids=[self.user1.pk],
            actor=self.superuser,
        )

        self.assertEqual(affected_ids, [self.user1.pk])
        self.assertFalse(
            self.role.user_set.filter(pk=self.user1.pk).exists()
        )

    def test_unassigned_user_cannot_be_removed(self):
        with self.assertRaises(ValidationError):
            RoleService.remove_users_from_role(
                role_id=self.role.pk,
                user_ids=[self.user1.pk],
                actor=self.superuser,
            )

    def test_mixed_assignment_removal_is_atomic(self):
        self.role.user_set.add(self.user1)

        with self.assertRaises(ValidationError):
            RoleService.remove_users_from_role(
                role_id=self.role.pk,
                user_ids=[self.user1.pk, self.user2.pk],
                actor=self.superuser,
            )

        self.assertTrue(
            self.role.user_set.filter(pk=self.user1.pk).exists()
        )

    def test_superuser_cannot_be_removed_from_regular_role(self):
        with self.assertRaises(ValidationError):
            RoleService.remove_users_from_role(
                role_id=self.role.pk,
                user_ids=[self.superuser.pk],
                actor=self.superuser,
            )