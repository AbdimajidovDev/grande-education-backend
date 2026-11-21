
from django.core.exceptions import (
    PermissionDenied as DjangoPermissionDenied,
    ValidationError as DjangoValidationError,
)
from rest_framework import serializers, status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.utils import extend_schema, OpenApiResponse

from apps.common.pagination import StandardResultsPagination
from apps.universities.api.permissions import (
    CanViewUniversityMajors,
    CanCreateUniversityMajor,
    CanUpdateUniversityMajor,
    CanDeleteUniversityMajor,
)
from apps.universities.api.cms.serializers.major_serializers import (
    UniversityMajorCreateSerializer,
    UniversityMajorUpdateSerializer,
    UniversityMajorDetailSerializer,
    UniversityMajorTranslationSetSerializer,
    UniversityMajorTranslationSerializer,
)
from apps.universities.selectors.university_revision_selector import (
    UniversityRevisionSelector,
)
from apps.universities.selectors.university_major_selector import (
    UniversityMajorSelector,
)
from apps.universities.services.university_major_service import (
    UniversityMajorService,
)


def handle_service_validation_error(exc):
    """Django ValidationError'ni DRF ValidationError'ga aylantiradi."""
    if hasattr(exc, "message_dict"):
        raise serializers.ValidationError(exc.message_dict)
    raise serializers.ValidationError(exc.messages)


class UniversityMajorListCreateAPIView(APIView):
    """Revision yo'nalishlarini ro'yxatlash va yaratish API."""

    pagination_class = StandardResultsPagination

    def get_permissions(self):
        permission_map = {
            "GET": CanViewUniversityMajors,
            "POST": CanCreateUniversityMajor,
        }
        permission_class = permission_map.get(self.request.method)
        if permission_class is None:
            return super().get_permissions()
        return [permission_class()]

    @extend_schema(
        operation_id="list_university_majors",
        tags=["Universities - Majors"],
        summary="Revision yo'nalishlarini olish",
        responses={
            200: UniversityMajorDetailSerializer(many=True),
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

        majors = UniversityMajorSelector.get_majors_by_revision(
            revision_id=revision_id,
        )

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(majors, request, view=self)
        serializer = UniversityMajorDetailSerializer(
            page,
            many=True,
            context={"request": request},
        )
        return paginator.get_paginated_response(serializer.data)

    @extend_schema(
        operation_id="create_university_major",
        tags=["Universities - Majors"],
        summary="Revision uchun yangi yo'nalish yaratish",
        request=UniversityMajorCreateSerializer,
        responses={
            201: UniversityMajorDetailSerializer,
            400: OpenApiResponse(description="Validation error."),
            401: OpenApiResponse(description="Authentication required."),
            403: OpenApiResponse(description="Insufficient permissions."),
            404: OpenApiResponse(description="Revision not found."),
        },
    )
    def post(self, request, revision_id):
        serializer = UniversityMajorCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            major = UniversityMajorService.create_major(
                actor=request.user,
                revision_id=revision_id,
                order=serializer.validated_data.get("order", 0),
                is_active=serializer.validated_data.get("is_active", True),
                translations=serializer.validated_data.get("translations"),
            )
        except DjangoValidationError as exc:
            handle_service_validation_error(exc)
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc))

        output_serializer = UniversityMajorDetailSerializer(
            major,
            context={"request": request},
        )
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)


class UniversityMajorDetailAPIView(APIView):
    """Yo'nalishni olish, tahrirlash va o'chirish API."""

    def get_permissions(self):
        permission_map = {
            "GET": CanViewUniversityMajors,
            "PATCH": CanUpdateUniversityMajor,
            "DELETE": CanDeleteUniversityMajor,
        }
        permission_class = permission_map.get(self.request.method)
        if permission_class is None:
            return super().get_permissions()
        return [permission_class()]

    @extend_schema(
        operation_id="get_university_major",
        tags=["Universities - Majors"],
        summary="Yo'nalish tafsilotlarini olish",
        responses={
            200: UniversityMajorDetailSerializer,
            401: OpenApiResponse(description="Authentication required."),
            403: OpenApiResponse(description="Insufficient permissions."),
            404: OpenApiResponse(description="Major not found."),
        },
    )
    def get(self, request, major_id):
        major = UniversityMajorSelector.get_major_by_id(major_id=major_id)
        if major is None:
            raise NotFound("Yo'nalish topilmadi.")

        serializer = UniversityMajorDetailSerializer(
            major,
            context={"request": request},
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        operation_id="update_university_major",
        tags=["Universities - Majors"],
        summary="Yo'nalishni tahrirlash",
        request=UniversityMajorUpdateSerializer,
        responses={
            200: UniversityMajorDetailSerializer,
            400: OpenApiResponse(description="Validation error."),
            401: OpenApiResponse(description="Authentication required."),
            403: OpenApiResponse(description="Insufficient permissions."),
            404: OpenApiResponse(description="Major not found."),
        },
    )
    def patch(self, request, major_id):
        serializer = UniversityMajorUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            major = UniversityMajorService.update_major(
                actor=request.user,
                major_id=major_id,
                order=serializer.validated_data.get("order"),
                is_active=serializer.validated_data.get("is_active"),
            )
        except DjangoValidationError as exc:
            handle_service_validation_error(exc)
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc))

        output_serializer = UniversityMajorDetailSerializer(
            major,
            context={"request": request},
        )
        return Response(output_serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        operation_id="delete_university_major",
        tags=["Universities - Majors"],
        summary="Yo'nalishni o'chirish",
        responses={
            204: OpenApiResponse(description="Successfully deleted."),
            400: OpenApiResponse(description="Validation error."),
            401: OpenApiResponse(description="Authentication required."),
            403: OpenApiResponse(description="Insufficient permissions."),
            404: OpenApiResponse(description="Major not found."),
        },
    )
    def delete(self, request, major_id):
        try:
            UniversityMajorService.delete_major(
                actor=request.user,
                major_id=major_id,
            )
        except DjangoValidationError as exc:
            handle_service_validation_error(exc)
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc))

        return Response(status=status.HTTP_204_NO_CONTENT)


class UniversityMajorTranslationAPIView(APIView):
    """Yo'nalish uchun til bo'yicha tarjima o'rnatish API."""

    def get_permissions(self):
        return [CanUpdateUniversityMajor()]

    @extend_schema(
        operation_id="set_university_major_translation",
        tags=["Universities - Majors"],
        summary="Yo'nalish tarjimasini yaratish yoki yangilash",
        request=UniversityMajorTranslationSetSerializer,
        responses={
            200: UniversityMajorTranslationSerializer,
            400: OpenApiResponse(description="Validation error."),
            401: OpenApiResponse(description="Authentication required."),
            403: OpenApiResponse(description="Insufficient permissions."),
            404: OpenApiResponse(description="Major not found."),
        },
    )
    def post(self, request, major_id):
        serializer = UniversityMajorTranslationSetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            trans = UniversityMajorService.set_major_translation(
                actor=request.user,
                major_id=major_id,
                language_code=serializer.validated_data["language_code"],
                title=serializer.validated_data["title"],
                description=serializer.validated_data.get("description", ""),
            )
        except DjangoValidationError as exc:
            handle_service_validation_error(exc)
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc))

        output_serializer = UniversityMajorTranslationSerializer(trans)
        return Response(output_serializer.data, status=status.HTTP_200_OK)
