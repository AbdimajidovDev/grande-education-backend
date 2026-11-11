
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
    CanViewUniversities,
    CanUpdateUniversity,
)

from apps.universities.api.cms.serializers.admission_period_serializers import (
    UniversityAdmissionPeriodCreateSerializer,
    UniversityAdmissionPeriodUpdateSerializer,
    UniversityAdmissionPeriodListSerializer,
)

from apps.universities.selectors.university_revision_selector import (
    UniversityRevisionSelector,
)
from apps.universities.selectors.university_admission_period_selector import (
    UniversityAdmissionPeriodSelector,
)

from apps.universities.services.university_admission_period_service import (
    UniversityAdmissionPeriodService,
)


def handle_service_validation_error(exc):
    """Django ValidationError'ni DRF ValidationError'ga aylantiradi."""

    if hasattr(exc, "message_dict"):
        raise serializers.ValidationError(exc.message_dict)

    raise serializers.ValidationError(exc.messages)


class UniversityAdmissionPeriodListCreateAPIView(APIView):
    """Revision qabul davrlarini ro'yxatlash va yaratish API."""

    pagination_class = StandardResultsPagination

    def get_permissions(self):
        permission_map = {
            "GET": CanViewUniversities,
            "POST": CanUpdateUniversity,
        }

        permission_class = permission_map.get(self.request.method)

        if permission_class is None:
            return super().get_permissions()

        return [permission_class()]

    @extend_schema(
        operation_id="list_university_admission_periods",
        tags=["Universities - Admission Periods"],
        summary="Revision qabul davrlarini olish",
        responses={
            200: UniversityAdmissionPeriodListSerializer(many=True),
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

        periods = (
            UniversityAdmissionPeriodSelector.get_periods_by_revision(
                revision_id=revision_id,
            )
        )

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(
            periods,
            request,
            view=self,
        )

        serializer = UniversityAdmissionPeriodListSerializer(
            page,
            many=True,
        )

        return paginator.get_paginated_response(serializer.data)

    @extend_schema(
        operation_id="create_university_admission_period",
        tags=["Universities - Admission Periods"],
        summary="Yangi qabul davrini yaratish",
        request=UniversityAdmissionPeriodCreateSerializer,
        responses={
            201: UniversityAdmissionPeriodListSerializer,
            400: OpenApiResponse(description="Invalid input or revision cannot be edited."),
            401: OpenApiResponse(description="Authentication required."),
            403: OpenApiResponse(description="Insufficient permissions."),
            404: OpenApiResponse(description="Revision not found."),
        },
    )
    def post(self, request, revision_id):
        serializer = UniversityAdmissionPeriodCreateSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        try:
            period = UniversityAdmissionPeriodService.create_period(
                actor=request.user,
                revision_id=revision_id,
                **serializer.validated_data,
            )
        except DjangoValidationError as exc:
            handle_service_validation_error(exc)
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc

        return Response(
            UniversityAdmissionPeriodListSerializer(period).data,
            status=status.HTTP_201_CREATED,
        )


class UniversityAdmissionPeriodDetailAPIView(APIView):
    """Qabul davrini tahrirlash va o'chirish API."""

    def get_permissions(self):
        permission_map = {
            "PATCH": CanUpdateUniversity,
            "DELETE": CanUpdateUniversity,
        }

        permission_class = permission_map.get(self.request.method)

        if permission_class is None:
            return super().get_permissions()

        return [permission_class()]

    @extend_schema(
        operation_id="update_university_admission_period",
        tags=["Universities - Admission Periods"],
        summary="Qabul davrini tahrirlash",
        request=UniversityAdmissionPeriodUpdateSerializer,
        responses={
            200: UniversityAdmissionPeriodListSerializer,
            400: OpenApiResponse(description="Invalid input or period cannot be edited."),
            401: OpenApiResponse(description="Authentication required."),
            403: OpenApiResponse(description="Insufficient permissions."),
            404: OpenApiResponse(description="Admission period not found."),
        },
    )
    def patch(self, request, period_id):
        period = (
            UniversityAdmissionPeriodSelector
            .get_period_queryset()
            .filter(pk=period_id)
            .first()
        )

        if period is None:
            raise NotFound("Qabul davri topilmadi.")

        serializer = UniversityAdmissionPeriodUpdateSerializer(
            period,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)

        try:
            updated_period = UniversityAdmissionPeriodService.update_period(
                actor=request.user,
                period_id=period_id,
                data=dict(serializer.validated_data),
            )
        except DjangoValidationError as exc:
            handle_service_validation_error(exc)
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc

        return Response(
            UniversityAdmissionPeriodListSerializer(updated_period).data,
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        operation_id="delete_university_admission_period",
        tags=["Universities - Admission Periods"],
        summary="Qabul davrini o'chirish",
        responses={
            204: OpenApiResponse(description="Admission period deleted."),
            400: OpenApiResponse(description="Period cannot be deleted."),
            401: OpenApiResponse(description="Authentication required."),
            403: OpenApiResponse(description="Insufficient permissions."),
            404: OpenApiResponse(description="Admission period not found."),
        },
    )
    def delete(self, request, period_id):
        try:
            UniversityAdmissionPeriodService.delete_period(
                actor=request.user,
                period_id=period_id,
            )
        except DjangoValidationError as exc:
            handle_service_validation_error(exc)
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc

        return Response(status=status.HTTP_204_NO_CONTENT)
