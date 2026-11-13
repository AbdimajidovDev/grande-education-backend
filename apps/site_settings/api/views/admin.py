
from rest_framework import status, viewsets
from rest_framework.parsers import JSONParser
from rest_framework.permissions import DjangoModelPermissions
from rest_framework.response import Response

from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
    OpenApiResponse,
)

from apps.site_settings.api.serializers import (
    SiteStatAdminSerializer,
    OfficeAdminSerializer,
)
from apps.site_settings.selectors import (
    get_admin_site_stats,
    get_admin_offices,
)
from apps.site_settings.services.site_stat_service import (
    create_site_stat,
    update_site_stat,
    delete_site_stat,
)

from apps.site_settings.services.contact_service import (
    create_office,
    update_office,
    delete_office,
)


class SiteStatModelPermissions(DjangoModelPermissions):
    perms_map = {
        "GET": ["%(app_label)s.view_%(model_name)s"],
        "OPTIONS": [],
        "HEAD": ["%(app_label)s.view_%(model_name)s"],
        "POST": ["%(app_label)s.add_%(model_name)s"],
        "PUT": ["%(app_label)s.change_%(model_name)s"],
        "PATCH": ["%(app_label)s.change_%(model_name)s"],
        "DELETE": ["%(app_label)s.delete_%(model_name)s"],
    }


class OfficeModelPermissions(DjangoModelPermissions):
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
        summary="Site statistics list",
        description="Barcha sayt statistikalarini tarjimalari bilan qaytaradi.",
        tags=["Site Settings - Admin"],
        responses={
            200: SiteStatAdminSerializer(many=True),
        },
    ),
    create=extend_schema(
        summary="Create site statistic",
        description="Yangi statistika va uning tarjimalarini yaratadi.",
        tags=["Site Settings - Admin"],
        request=SiteStatAdminSerializer,
        responses={
            201: SiteStatAdminSerializer,
            400: OpenApiResponse(description="Validation error"),
        },
    ),
    retrieve=extend_schema(
        summary="Site statistic detail",
        description="ID orqali bitta statistikani qaytaradi.",
        tags=["Site Settings - Admin"],
        responses={
            200: SiteStatAdminSerializer,
            404: OpenApiResponse(description="Statistic not found"),
        },
    ),
    update=extend_schema(
        summary="Update site statistic",
        description="Statistika va barcha tarjimalarini to'liq yangilaydi.",
        tags=["Site Settings - Admin"],
        request=SiteStatAdminSerializer,
        responses={
            200: SiteStatAdminSerializer,
            400: OpenApiResponse(description="Validation error"),
            404: OpenApiResponse(description="Statistic not found"),
        },
    ),
    partial_update=extend_schema(
        summary="Partial update site statistic",
        description="Statistika ma'lumotlarini qisman yangilaydi.",
        tags=["Site Settings - Admin"],
        request=SiteStatAdminSerializer,
        responses={
            200: SiteStatAdminSerializer,
            400: OpenApiResponse(description="Validation error"),
            404: OpenApiResponse(description="Statistic not found"),
        },
    ),
    destroy=extend_schema(
        summary="Delete site statistic",
        description="Statistikani va uning tarjimalarini o'chiradi.",
        tags=["Site Settings - Admin"],
        responses={
            204: OpenApiResponse(description="Statistic successfully deleted"),
            404: OpenApiResponse(description="Statistic not found"),
        },
    ),
)
class SiteStatViewSet(viewsets.ModelViewSet):
    serializer_class = SiteStatAdminSerializer
    permission_classes = [SiteStatModelPermissions]
    parser_classes = [JSONParser]

    def get_queryset(self):
        return get_admin_site_stats()

    def perform_create(self, serializer):
        stat = create_site_stat(
            validated_data=serializer.validated_data.copy(),
        )
        serializer.instance = stat

    def perform_update(self, serializer):
        stat = update_site_stat(
            stat=serializer.instance,
            validated_data=serializer.validated_data.copy(),
            replace_translations=self.request.method == "PUT",
        )
        serializer.instance = stat

    def perform_destroy(self, instance):
        delete_site_stat(stat=instance)


@extend_schema_view(
    list=extend_schema(
        summary="Offices list",
        description="Barcha ofislarni kontakt ma'lumotlari bilan qaytaradi.",
        tags=["Site Settings - Admin"],
        responses={
            200: OfficeAdminSerializer(many=True),
        },
    ),
    create=extend_schema(
        summary="Create office",
        description="Yangi ofis va unga tegishli kontakt ma'lumotlarini yaratadi.",
        tags=["Site Settings - Admin"],
        request=OfficeAdminSerializer,
        responses={
            201: OfficeAdminSerializer,
            400: OpenApiResponse(description="Validation error"),
        },
    ),
    retrieve=extend_schema(
        summary="Office detail",
        description="ID orqali bitta ofis ma'lumotlarini qaytaradi.",
        tags=["Site Settings - Admin"],
        responses={
            200: OfficeAdminSerializer,
            404: OpenApiResponse(description="Office not found"),
        },
    ),
    update=extend_schema(
        summary="Update office",
        description="Ofis va yuborilgan bog'langan ma'lumotlarni yangilaydi.",
        tags=["Site Settings - Admin"],
        request=OfficeAdminSerializer,
        responses={
            200: OfficeAdminSerializer,
            400: OpenApiResponse(description="Validation error"),
            404: OpenApiResponse(description="Office not found"),
        },
    ),
    partial_update=extend_schema(
        summary="Partial update office",
        description="Ofis ma'lumotlarini qisman yangilaydi.",
        tags=["Site Settings - Admin"],
        request=OfficeAdminSerializer,
        responses={
            200: OfficeAdminSerializer,
            400: OpenApiResponse(description="Validation error"),
            404: OpenApiResponse(description="Office not found"),
        },
    ),
    destroy=extend_schema(
        summary="Delete office",
        description="Ofis va unga bog'langan ma'lumotlarni o'chiradi.",
        tags=["Site Settings - Admin"],
        responses={
            204: OpenApiResponse(description="Office successfully deleted"),
            404: OpenApiResponse(description="Office not found"),
        },
    ),
)
class OfficeViewSet(viewsets.ModelViewSet):
    serializer_class = OfficeAdminSerializer
    permission_classes = [OfficeModelPermissions]
    parser_classes = [JSONParser]

    def get_queryset(self):
        return get_admin_offices()

    def perform_create(self, serializer):
        office = create_office(
            validated_data=serializer.validated_data.copy(),
        )
        serializer.instance = office

    def perform_update(self, serializer):
        office = update_office(
            office=serializer.instance,
            validated_data=serializer.validated_data.copy(),
        )
        serializer.instance = office

    def perform_destroy(self, instance):
        delete_office(office=instance)
