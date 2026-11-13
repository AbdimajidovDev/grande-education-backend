
from rest_framework import status, viewsets
from rest_framework.parsers import (
    JSONParser,
    MultiPartParser,
    FormParser,
)
from rest_framework.permissions import DjangoModelPermissions

from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
    OpenApiResponse,
)

from apps.partners.api.serializers import PartnerAdminSerializer
from apps.partners.selectors import get_admin_partners
from apps.partners.services import (
    create_partner,
    update_partner,
    delete_partner,
)


class PartnerModelPermissions(DjangoModelPermissions):
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
        summary="Partners list",
        description="Barcha hamkorlar ro'yxatini qaytaradi.",
        tags=["Partners - Admin"],
        responses={200: PartnerAdminSerializer(many=True)},
    ),
    create=extend_schema(
        summary="Create partner",
        description="Yangi hamkor yaratadi.",
        tags=["Partners - Admin"],
        request=PartnerAdminSerializer,
        responses={
            201: PartnerAdminSerializer,
            400: OpenApiResponse(description="Validation error"),
        },
    ),
    retrieve=extend_schema(
        summary="Partner detail",
        description="ID orqali bitta hamkor ma'lumotlarini qaytaradi.",
        tags=["Partners - Admin"],
        responses={
            200: PartnerAdminSerializer,
            404: OpenApiResponse(description="Partner not found"),
        },
    ),
    update=extend_schema(
        summary="Update partner",
        description="Hamkor ma'lumotlarini to'liq yangilaydi.",
        tags=["Partners - Admin"],
        request=PartnerAdminSerializer,
        responses={
            200: PartnerAdminSerializer,
            400: OpenApiResponse(description="Validation error"),
            404: OpenApiResponse(description="Partner not found"),
        },
    ),
    partial_update=extend_schema(
        summary="Partial update partner",
        description="Hamkor ma'lumotlarini qisman yangilaydi.",
        tags=["Partners - Admin"],
        request=PartnerAdminSerializer,
        responses={
            200: PartnerAdminSerializer,
            400: OpenApiResponse(description="Validation error"),
            404: OpenApiResponse(description="Partner not found"),
        },
    ),
    destroy=extend_schema(
        summary="Delete partner",
        description="Hamkorni o'chiradi.",
        tags=["Partners - Admin"],
        responses={
            204: OpenApiResponse(description="Partner successfully deleted"),
            404: OpenApiResponse(description="Partner not found"),
        },
    ),
)
class PartnerViewSet(viewsets.ModelViewSet):
    serializer_class = PartnerAdminSerializer
    permission_classes = [PartnerModelPermissions]
    parser_classes = [
        JSONParser,
        MultiPartParser,
        FormParser,
    ]

    def get_queryset(self):
        return get_admin_partners()

    def perform_create(self, serializer):
        partner = create_partner(
            validated_data=serializer.validated_data.copy(),
        )
        serializer.instance = partner

    def perform_update(self, serializer):
        partner = update_partner(
            partner=serializer.instance,
            validated_data=serializer.validated_data.copy(),
        )
        serializer.instance = partner

    def perform_destroy(self, instance):
        delete_partner(partner=instance)
