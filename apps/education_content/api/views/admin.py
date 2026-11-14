from django.db.models import QuerySet

from rest_framework import status, viewsets
from rest_framework.parsers import (
    FormParser,
    JSONParser,
    MultiPartParser,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import DjangoModelPermissions

from drf_spectacular.utils import extend_schema, extend_schema_view

from apps.education_content.models import (
    HybridTeacher,
    LearningComponent,
)
from apps.education_content.selectors import (
    get_admin_hybrid_teachers,
    get_admin_learning_components,
)
from apps.education_content.services.hybrid_service import (
    create_hybrid_teacher,
    update_hybrid_teacher,
    delete_hybrid_teacher,
    create_learning_component,
    update_learning_component,
    delete_learning_component,
)
from apps.education_content.api.serializers import (
    HybridTeacherAdminSerializer,
    LearningComponentAdminSerializer,
)

from apps.education_content.models import (
    UniversityStep,
    UniversityStepPage,
)
from apps.education_content.selectors import (
    get_admin_university_step_pages,
    get_admin_university_steps,
)
from apps.education_content.services.university_step_service import (
    create_university_step_page,
    update_university_step_page,
    delete_university_step_page,
    create_university_step,
    update_university_step,
    delete_university_step,
)
from apps.education_content.api.serializers import (
    UniversityStepPageAdminSerializer,
    UniversityStepAdminSerializer,
)


# =========================================================
# Permissions
# =========================================================

class HybridTeacherModelPermissions(DjangoModelPermissions):
    perms_map = {
        "GET": ["%(app_label)s.view_%(model_name)s"],
        "OPTIONS": [],
        "HEAD": ["%(app_label)s.view_%(model_name)s"],
        "POST": ["%(app_label)s.add_%(model_name)s"],
        "PUT": ["%(app_label)s.change_%(model_name)s"],
        "PATCH": ["%(app_label)s.change_%(model_name)s"],
        "DELETE": ["%(app_label)s.delete_%(model_name)s"],
    }


class LearningComponentModelPermissions(DjangoModelPermissions):
    perms_map = {
        "GET": ["%(app_label)s.view_%(model_name)s"],
        "OPTIONS": [],
        "HEAD": ["%(app_label)s.view_%(model_name)s"],
        "POST": ["%(app_label)s.add_%(model_name)s"],
        "PUT": ["%(app_label)s.change_%(model_name)s"],
        "PATCH": ["%(app_label)s.change_%(model_name)s"],
        "DELETE": ["%(app_label)s.delete_%(model_name)s"],
    }


class UniversityStepPageModelPermissions(DjangoModelPermissions):
    perms_map = {
        "GET": ["%(app_label)s.view_%(model_name)s"],
        "OPTIONS": [],
        "HEAD": ["%(app_label)s.view_%(model_name)s"],
        "POST": ["%(app_label)s.add_%(model_name)s"],
        "PUT": ["%(app_label)s.change_%(model_name)s"],
        "PATCH": ["%(app_label)s.change_%(model_name)s"],
        "DELETE": ["%(app_label)s.delete_%(model_name)s"],
    }


class UniversityStepModelPermissions(DjangoModelPermissions):
    perms_map = {
        "GET": ["%(app_label)s.view_%(model_name)s"],
        "OPTIONS": [],
        "HEAD": ["%(app_label)s.view_%(model_name)s"],
        "POST": ["%(app_label)s.add_%(model_name)s"],
        "PUT": ["%(app_label)s.change_%(model_name)s"],
        "PATCH": ["%(app_label)s.change_%(model_name)s"],
        "DELETE": ["%(app_label)s.delete_%(model_name)s"],
    }


# =========================================================
# Hybrid Teacher ViewSet
# =========================================================

@extend_schema_view(
    list=extend_schema(
        tags=["Admin - Education Content"],
        summary="List hybrid teachers",
    ),
    retrieve=extend_schema(
        tags=["Admin - Education Content"],
        summary="Retrieve hybrid teacher",
    ),
    create=extend_schema(
        tags=["Admin - Education Content"],
        summary="Create hybrid teacher",
    ),
    update=extend_schema(
        tags=["Admin - Education Content"],
        summary="Update hybrid teacher",
    ),
    partial_update=extend_schema(
        tags=["Admin - Education Content"],
        summary="Partially update hybrid teacher",
    ),
    destroy=extend_schema(
        tags=["Admin - Education Content"],
        summary="Delete hybrid teacher",
    ),
)
class HybridTeacherViewSet(ModelViewSet):
    serializer_class = HybridTeacherAdminSerializer
    permission_classes = [
        IsAuthenticated,
        HybridTeacherModelPermissions,
    ]
    parser_classes = [
        JSONParser,
        MultiPartParser,
        FormParser,
    ]

    def get_queryset(self) -> QuerySet:
        return get_admin_hybrid_teachers()

    def perform_create(self, serializer):
        serializer.instance = create_hybrid_teacher(
            **serializer.validated_data,
        )

    def perform_update(self, serializer):
        serializer.instance = update_hybrid_teacher(
            teacher=serializer.instance,
            **serializer.validated_data,
        )

    def perform_destroy(self, instance):
        delete_hybrid_teacher(teacher=instance)


# =========================================================
# Learning Component ViewSet
# =========================================================

@extend_schema_view(
    list=extend_schema(
        tags=["Admin - Education Content"],
        summary="List learning components",
    ),
    retrieve=extend_schema(
        tags=["Admin - Education Content"],
        summary="Retrieve learning component",
    ),
    create=extend_schema(
        tags=["Admin - Education Content"],
        summary="Create learning component",
    ),
    update=extend_schema(
        tags=["Admin - Education Content"],
        summary="Update learning component",
    ),
    partial_update=extend_schema(
        tags=["Admin - Education Content"],
        summary="Partially update learning component",
    ),
    destroy=extend_schema(
        tags=["Admin - Education Content"],
        summary="Delete learning component",
    ),
)
class LearningComponentViewSet(ModelViewSet):
    serializer_class = LearningComponentAdminSerializer
    permission_classes = [
        IsAuthenticated,
        LearningComponentModelPermissions,
    ]
    parser_classes = [
        JSONParser,
        MultiPartParser,
        FormParser,
    ]

    def get_queryset(self) -> QuerySet:
        return get_admin_learning_components()

    def perform_create(self, serializer):
        serializer.instance = create_learning_component(
            **serializer.validated_data,
        )

    def perform_update(self, serializer):
        serializer.instance = update_learning_component(
            component=serializer.instance,
            **serializer.validated_data,
        )

    def perform_destroy(self, instance):
        delete_learning_component(component=instance)


# ============================================================

@extend_schema_view(
    list=extend_schema(
        tags=["Admin - Education Content"],
        summary="List university step pages",
    ),
    retrieve=extend_schema(
        tags=["Admin - Education Content"],
        summary="Retrieve university step page",
    ),
    create=extend_schema(
        tags=["Admin - Education Content"],
        summary="Create university step page",
    ),
    update=extend_schema(
        tags=["Admin - Education Content"],
        summary="Update university step page",
    ),
    partial_update=extend_schema(
        tags=["Admin - Education Content"],
        summary="Partially update university step page",
    ),
    destroy=extend_schema(
        tags=["Admin - Education Content"],
        summary="Delete university step page",
    ),
)
class UniversityStepPageViewSet(ModelViewSet):
    serializer_class = UniversityStepPageAdminSerializer
    permission_classes = [
        IsAuthenticated,
        UniversityStepPageModelPermissions,
    ]
    parser_classes = [
        JSONParser,
        MultiPartParser,
        FormParser,
    ]

    def get_queryset(self):
        return get_admin_university_step_pages()

    def perform_create(self, serializer):
        serializer.instance = create_university_step_page(
            **serializer.validated_data,
        )

    def perform_update(self, serializer):
        serializer.instance = update_university_step_page(
            page=serializer.instance,
            **serializer.validated_data,
        )

    def perform_destroy(self, instance):
        delete_university_step_page(page=instance)


@extend_schema_view(
    list=extend_schema(
        tags=["Admin - Education Content"],
        summary="List university steps",
    ),
    retrieve=extend_schema(
        tags=["Admin - Education Content"],
        summary="Retrieve university step",
    ),
    create=extend_schema(
        tags=["Admin - Education Content"],
        summary="Create university step",
    ),
    update=extend_schema(
        tags=["Admin - Education Content"],
        summary="Update university step",
    ),
    partial_update=extend_schema(
        tags=["Admin - Education Content"],
        summary="Partially update university step",
    ),
    destroy=extend_schema(
        tags=["Admin - Education Content"],
        summary="Delete university step",
    ),
)
class UniversityStepViewSet(ModelViewSet):
    serializer_class = UniversityStepAdminSerializer
    permission_classes = [
        IsAuthenticated,
        UniversityStepModelPermissions,
    ]
    parser_classes = [
        JSONParser,
        MultiPartParser,
        FormParser,
    ]

    def get_queryset(self):
        return get_admin_university_steps()

    def perform_create(self, serializer):
        serializer.instance = create_university_step(
            **serializer.validated_data,
        )

    def perform_update(self, serializer):
        serializer.instance = update_university_step(
            step=serializer.instance,
            **serializer.validated_data,
        )

    def perform_destroy(self, instance):
        delete_university_step(step=instance)

