
from django.core.exceptions import (
    PermissionDenied as DjangoPermissionDenied,
    ValidationError as DjangoValidationError,
)
from rest_framework import serializers, status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.utils import extend_schema, OpenApiResponse

from apps.common.pagination import StandardResultsPagination
from apps.universities.api.permissions import (
    CanViewUniversityMedia,
    CanCreateUniversityMedia,
    CanUpdateUniversityMedia,
    CanDeleteUniversityMedia,
)
from apps.universities.api.cms.serializers.media_serializers import (
    UniversityMediaCreateSerializer,
    UniversityMediaUpdateSerializer,
    UniversityMediaDetailSerializer,
)
from apps.universities.selectors.university_revision_selector import (
    UniversityRevisionSelector,
)
from apps.universities.selectors.university_media_selector import (
    UniversityMediaSelector,
)
from apps.universities.services.university_media_service import (
    UniversityMediaService,
)


def handle_service_validation_error(exc):
    """Django ValidationError'ni DRF ValidationError'ga aylantiradi."""
    if hasattr(exc, "message_dict"):
        raise serializers.ValidationError(exc.message_dict)
    raise serializers.ValidationError(exc.messages)


class UniversityMediaListCreateAPIView(APIView):
    """Revision media fayllarini ro'yxatlash va yuklash API."""

    parser_classes = [MultiPartParser, FormParser, JSONParser]
    pagination_class = StandardResultsPagination

    def get_permissions(self):
        permission_map = {
            "GET": CanViewUniversityMedia,
            "POST": CanCreateUniversityMedia,
        }
        permission_class = permission_map.get(self.request.method)
        if permission_class is None:
            return super().get_permissions()
        return [permission_class()]

    @extend_schema(
        operation_id="list_university_media",
        tags=["Universities - Media"],
        summary="Revision media fayllarini olish",
        responses={
            200: UniversityMediaDetailSerializer(many=True),
            401: OpenApiResponse(description="Authentication required."),
            403: OpenApiResponse(description="Insufficient permissions."),
            404: OpenApiResponse(description="Revision not found."),
        },
    )
    def get(self, request, revision_id):
        revision = UniversityRevisionSelector.get_revision_by_id(
            revision_id=revision_id,
        )
        if revision is None:
            raise NotFound("Universitet revisioni topilmadi.")

        media_type = request.query_params.get("media_type")
        media_items = UniversityMediaSelector.get_media_by_revision(
            revision_id=revision_id,
            media_type=media_type,
        )

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(media_items, request, view=self)
        serializer = UniversityMediaDetailSerializer(
            page,
            many=True,
            context={"request": request},
        )
        return paginator.get_paginated_response(serializer.data)

    @extend_schema(
        operation_id="create_university_media",
        tags=["Universities - Media"],
        summary="Revision uchun yangi media fayl yuklash",
        request=UniversityMediaCreateSerializer,
        responses={
            201: UniversityMediaDetailSerializer,
            400: OpenApiResponse(description="Validation error."),
            401: OpenApiResponse(description="Authentication required."),
            403: OpenApiResponse(description="Insufficient permissions."),
            404: OpenApiResponse(description="Revision not found."),
        },
    )
    def post(self, request, revision_id):
        serializer = UniversityMediaCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            media = UniversityMediaService.create_media(
                actor=request.user,
                revision_id=revision_id,
                file=serializer.validated_data["file"],
                media_type=serializer.validated_data.get("media_type", "gallery"),
                order=serializer.validated_data.get("order", 0),
                caption=serializer.validated_data.get("caption", ""),
            )
        except DjangoValidationError as exc:
            handle_service_validation_error(exc)
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc))

        output_serializer = UniversityMediaDetailSerializer(
            media,
            context={"request": request},
        )
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)


class UniversityMediaDetailAPIView(APIView):
    """Media faylni olish, tahrirlash va o'chirish API."""

    def get_permissions(self):
        permission_map = {
            "GET": CanViewUniversityMedia,
            "PATCH": CanUpdateUniversityMedia,
            "DELETE": CanDeleteUniversityMedia,
        }
        permission_class = permission_map.get(self.request.method)
        if permission_class is None:
            return super().get_permissions()
        return [permission_class()]

    @extend_schema(
        operation_id="get_university_media_detail",
        tags=["Universities - Media"],
        summary="Media fayl tafsilotlarini olish",
        responses={
            200: UniversityMediaDetailSerializer,
            401: OpenApiResponse(description="Authentication required."),
            403: OpenApiResponse(description="Insufficient permissions."),
            404: OpenApiResponse(description="Media not found."),
        },
    )
    def get(self, request, media_id):
        media = UniversityMediaSelector.get_media_by_id(media_id=media_id)
        if media is None:
            raise NotFound("Media fayl topilmadi.")

        serializer = UniversityMediaDetailSerializer(
            media,
            context={"request": request},
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        operation_id="update_university_media",
        tags=["Universities - Media"],
        summary="Media fayl metama'lumotlarini yangilash",
        request=UniversityMediaUpdateSerializer,
        responses={
            200: UniversityMediaDetailSerializer,
            400: OpenApiResponse(description="Validation error."),
            401: OpenApiResponse(description="Authentication required."),
            403: OpenApiResponse(description="Insufficient permissions."),
            404: OpenApiResponse(description="Media not found."),
        },
    )
    def patch(self, request, media_id):
        serializer = UniversityMediaUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            media = UniversityMediaService.update_media(
                actor=request.user,
                media_id=media_id,
                media_type=serializer.validated_data.get("media_type"),
                order=serializer.validated_data.get("order"),
                caption=serializer.validated_data.get("caption"),
            )
        except DjangoValidationError as exc:
            handle_service_validation_error(exc)
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc))

        output_serializer = UniversityMediaDetailSerializer(
            media,
            context={"request": request},
        )
        return Response(output_serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        operation_id="delete_university_media",
        tags=["Universities - Media"],
        summary="Media faylni o'chirish",
        responses={
            204: OpenApiResponse(description="Successfully deleted."),
            400: OpenApiResponse(description="Validation error."),
            401: OpenApiResponse(description="Authentication required."),
            403: OpenApiResponse(description="Insufficient permissions."),
            404: OpenApiResponse(description="Media not found."),
        },
    )
    def delete(self, request, media_id):
        try:
            UniversityMediaService.delete_media(
                actor=request.user,
                media_id=media_id,
            )
        except DjangoValidationError as exc:
            handle_service_validation_error(exc)
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc))

        return Response(status=status.HTTP_204_NO_CONTENT)
