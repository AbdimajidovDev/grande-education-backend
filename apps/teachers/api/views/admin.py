
from rest_framework import viewsets
from rest_framework.parsers import (
    JSONParser,
    MultiPartParser,
    FormParser,
)
from rest_framework.permissions import DjangoModelPermissions

from apps.teachers.api.serializers import TeacherAdminSerializer
from apps.teachers.selectors import get_admin_teachers
from apps.teachers.services import (
    create_teacher,
    update_teacher,
    delete_teacher,
)


class TeacherModelPermissions(DjangoModelPermissions):
    perms_map = {
        "GET": ["%(app_label)s.view_%(model_name)s"],
        "OPTIONS": [],
        "HEAD": ["%(app_label)s.view_%(model_name)s"],
        "POST": ["%(app_label)s.add_%(model_name)s"],
        "PUT": ["%(app_label)s.change_%(model_name)s"],
        "PATCH": ["%(app_label)s.change_%(model_name)s"],
        "DELETE": ["%(app_label)s.delete_%(model_name)s"],
    }


class TeacherViewSet(viewsets.ModelViewSet):
    serializer_class = TeacherAdminSerializer
    permission_classes = [TeacherModelPermissions]
    parser_classes = [
        JSONParser,
        MultiPartParser,
        FormParser,
    ]

    def get_queryset(self):
        return get_admin_teachers()

    def perform_create(self, serializer):
        teacher = create_teacher(
            validated_data=serializer.validated_data.copy()
        )
        serializer.instance = teacher

    def perform_update(self, serializer):
        teacher = update_teacher(
            teacher=serializer.instance,
            validated_data=serializer.validated_data.copy(),
        )
        serializer.instance = teacher

    def perform_destroy(self, instance):
        delete_teacher(teacher=instance)
