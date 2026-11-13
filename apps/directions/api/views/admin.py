
from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
    OpenApiResponse,
)
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import DjangoModelPermissions

from apps.directions.api.serializers import DirectionAdminSerializer
from apps.directions.selectors import get_admin_directions
from apps.directions.services import (
    create_direction,
    update_direction,
    delete_direction,
)


class DirectionModelPermissions(DjangoModelPermissions):
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
        tags=["Directions - Admin"],
        summary="List all directions",
        responses={200: DirectionAdminSerializer(many=True)},
    ),
    create=extend_schema(
        tags=["Directions - Admin"],
        summary="Create a direction",
        request=DirectionAdminSerializer,
        responses={
            201: DirectionAdminSerializer,
            400: OpenApiResponse(description="Validation error."),
        },
    ),
    retrieve=extend_schema(
        tags=["Directions - Admin"],
        summary="Retrieve a direction",
        responses={
            200: DirectionAdminSerializer,
            404: OpenApiResponse(description="Direction not found."),
        },
    ),
    update=extend_schema(
        tags=["Directions - Admin"],
        summary="Update a direction",
        request=DirectionAdminSerializer,
        responses={
            200: DirectionAdminSerializer,
            400: OpenApiResponse(description="Validation error."),
            404: OpenApiResponse(description="Direction not found."),
        },
    ),
    partial_update=extend_schema(
        tags=["Directions - Admin"],
        summary="Partially update a direction",
        request=DirectionAdminSerializer,
        responses={
            200: DirectionAdminSerializer,
            400: OpenApiResponse(description="Validation error."),
            404: OpenApiResponse(description="Direction not found."),
        },
    ),
    destroy=extend_schema(
        tags=["Directions - Admin"],
        summary="Delete a direction",
        responses={
            204: None,
            404: OpenApiResponse(description="Direction not found."),
        },
    ),
)
class DirectionAdminViewSet(ModelViewSet):
    serializer_class = DirectionAdminSerializer
    permission_classes = [DirectionModelPermissions]
    http_method_names = [
        "get",
        "post",
        "put",
        "patch",
        "delete",
        "head",
        "options",
    ]

    def get_queryset(self):
        return get_admin_directions()

    def perform_create(self, serializer):
        direction = create_direction(
            validated_data=serializer.validated_data.copy(),
        )
        serializer.instance = direction

    def perform_update(self, serializer):
        direction = update_direction(
            direction=serializer.instance,
            validated_data=serializer.validated_data.copy(),
            replace_translations=self.request.method == "PUT",
        )
        serializer.instance = direction

    def perform_destroy(self, instance):
        delete_direction(direction=instance)
