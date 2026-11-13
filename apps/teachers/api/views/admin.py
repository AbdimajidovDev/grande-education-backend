
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
from drf_spectacular.utils import extend_schema, extend_schema_view


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


@extend_schema_view(
    list=extend_schema(
        summary="Teachers list",
        description="Barcha o'qituvchilar ro'yxatini qaytaradi.",
        tags=["Teachers - Admin"],
    ),
    create=extend_schema(
        summary="Create teacher",
        description="Yangi o'qituvchi va uning tarjimalarini yaratadi.",
        tags=["Teachers - Admin"],
    ),
    retrieve=extend_schema(
        summary="Teacher detail",
        description="ID orqali bitta o'qituvchi ma'lumotlarini qaytaradi.",
        tags=["Teachers - Admin"],
    ),
    update=extend_schema(
        summary="Update teacher",
        description="O'qituvchi ma'lumotlarini to'liq yangilaydi.",
        tags=["Teachers - Admin"],
    ),
    partial_update=extend_schema(
        summary="Partial update teacher",
        description="O'qituvchi ma'lumotlarini qisman yangilaydi.",
        tags=["Teachers - Admin"],
    ),
    destroy=extend_schema(
        summary="Delete teacher",
        description="O'qituvchini o'chiradi.",
        tags=["Teachers - Admin"],
    ),
)
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
