
from rest_framework.permissions import BasePermission


class HasUniversityPermission(BasePermission):
    """Universitet moduli uchun Django permissionlarini tekshiradi."""

    permission_codename = None

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        if user.is_superuser:
            return True

        if not self.permission_codename:
            return False

        return user.has_perm(
            f"universities.{self.permission_codename}"
        )


class CanViewUniversity(HasUniversityPermission):
    permission_codename = "view_university"


class CanAddUniversity(HasUniversityPermission):
    permission_codename = "add_university"


class CanChangeUniversity(HasUniversityPermission):
    permission_codename = "change_university"


class CanDeleteUniversity(HasUniversityPermission):
    permission_codename = "delete_university"


class CanSubmitUniversityForReview(HasUniversityPermission):
    permission_codename = "submit_review_university"


class CanApproveUniversity(HasUniversityPermission):
    permission_codename = "approve_university"


class CanRejectUniversity(HasUniversityPermission):
    permission_codename = "reject_university"


class CanPublishUniversity(HasUniversityPermission):
    permission_codename = "publish_university"
