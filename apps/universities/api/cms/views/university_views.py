
from django.core.exceptions import (
    PermissionDenied as DjangoPermissionDenied,
    ValidationError as DjangoValidationError,
)

from rest_framework import serializers, status
from rest_framework.exceptions import PermissionDenied as DRFPermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.utils import extend_schema, OpenApiResponse

from apps.common.pagination import StandardResultsPagination

from apps.universities.api.permissions import (
    CanViewUniversities,
    CanCreateUniversity,
)
from apps.universities.api.cms.serializers.university_serializers import (
    UniversityCreateSerializer,
    UniversityListSerializer,
)
from apps.universities.selectors.university_selector import UniversitySelector
from apps.universities.services.university_service import UniversityService


def handle_service_validation_error(exc):
    """Django ValidationError'ni DRF ValidationError'ga aylantiradi."""

    if hasattr(exc, "message_dict"):
        raise serializers.ValidationError(exc.message_dict)

    raise serializers.ValidationError(exc.messages)


class UniversityListCreateAPIView(APIView):
    """Universitetlarni ro'yxatlash va yaratish API."""

    pagination_class = StandardResultsPagination

    def get_permissions(self):
        permission_map = {
            "GET": CanViewUniversities,
            "POST": CanCreateUniversity,
        }

        permission_class = permission_map.get(
            self.request.method,
        )

        if permission_class is None:
            return super().get_permissions()

        return [permission_class()]

    @extend_schema(
        operation_id="list_universities",
        tags=["Universities - CMS"],
        summary="Universitetlar ro'yxatini olish",
        responses={
            200: UniversityListSerializer(many=True),
            401: OpenApiResponse(description="Authentication required."),
            403: OpenApiResponse(description="Insufficient permissions."),
        },
    )
    def get(self, request):
        universities = UniversitySelector.get_university_queryset()

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(
            universities,
            request,
            view=self,
        )

        serializer = UniversityListSerializer(
            page,
            many=True,
        )

        return paginator.get_paginated_response(serializer.data)

    @extend_schema(
        operation_id="create_university",
        tags=["Universities - CMS"],
        summary="Yangi universitet yaratish",
        request=UniversityCreateSerializer,
        responses={
            201: UniversityListSerializer,
            400: OpenApiResponse(description="Invalid input."),
            401: OpenApiResponse(description="Authentication required."),
            403: OpenApiResponse(description="Insufficient permissions."),
        },
    )
    def post(self, request):
        serializer = UniversityCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            university = UniversityService.create_university(
                actor=request.user,
                **serializer.validated_data,
            )
        except DjangoValidationError as exc:
            handle_service_validation_error(exc)
        except DjangoPermissionDenied as exc:
            raise DRFPermissionDenied(str(exc)) from exc

        return Response(
            UniversityListSerializer(university).data,
            status=status.HTTP_201_CREATED,
        )



from rest_framework.exceptions import NotFound

from apps.universities.api.permissions import CanViewUniversities
from apps.universities.api.cms.serializers.university_serializers import (
    UniversityDetailSerializer,
)
from apps.universities.selectors.university_selector import UniversitySelector


class UniversityDetailAPIView(APIView):
    """Bitta universitet haqida batafsil ma'lumot olish API."""

    permission_classes = [CanViewUniversities]

    @extend_schema(
        operation_id="retrieve_university",
        tags=["Universities - CMS"],
        summary="Universitet ma'lumotlarini olish",
        responses={
            200: UniversityDetailSerializer,
            401: OpenApiResponse(description="Authentication required."),
            403: OpenApiResponse(description="Insufficient permissions."),
            404: OpenApiResponse(description="University not found."),
        },
    )
    def get(self, request, university_id):
        university = UniversitySelector.get_university_by_id(
            university_id=university_id,
        )

        if university is None:
            raise NotFound("Universitet topilmadi.")

        serializer = UniversityDetailSerializer(university)

        return Response(serializer.data)

