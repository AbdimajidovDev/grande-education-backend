
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
from apps.universities.api.cms.serializers.revision_serializers import (
    UniversityRevisionCreateSerializer,
    UniversityRevisionListSerializer,
    UniversityRevisionUpdateSerializer,
    UniversityRevisionDetailSerializer,
)
from apps.universities.selectors.university_selector import UniversitySelector
from apps.universities.selectors.university_revision_selector import (
    UniversityRevisionSelector,
)
from apps.universities.services.university_revision_service import (
    UniversityRevisionService,
)

from apps.universities.api.permissions import (
    CanSubmitUniversityForReview,
)
from apps.universities.api.permissions import CanApproveUniversity
from apps.universities.api.permissions import CanRejectUniversity

from apps.universities.api.cms.serializers.revision_serializers import (
    UniversityRevisionRejectSerializer,
)
from apps.universities.api.permissions import CanPublishUniversity



def handle_service_validation_error(exc):
    """Django ValidationError'ni DRF ValidationError'ga aylantiradi."""

    if hasattr(exc, "message_dict"):
        raise serializers.ValidationError(exc.message_dict)

    raise serializers.ValidationError(exc.messages)


class UniversityRevisionListCreateAPIView(APIView):
    """Universitet revisionlarini ro'yxatlash va yaratish API."""

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
        operation_id="list_university_revisions",
        tags=["Universities - Revisions"],
        summary="Universitet revisionlari tarixini olish",
        responses={
            200: UniversityRevisionListSerializer(many=True),
            401: OpenApiResponse(description="Authentication required."),
            403: OpenApiResponse(description="Insufficient permissions."),
            404: OpenApiResponse(description="University not found."),
        },
    )
    def get(self, request, university_id):
        if UniversitySelector.get_university_by_id(university_id) is None:
            raise NotFound("Universitet topilmadi.")

        revisions = UniversityRevisionSelector.get_revisions_by_university(
            university_id=university_id,
        )

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(
            revisions,
            request,
            view=self,
        )

        serializer = UniversityRevisionListSerializer(page, many=True)

        return paginator.get_paginated_response(serializer.data)

    @extend_schema(
        operation_id="create_university_revision",
        tags=["Universities - Revisions"],
        summary="Yangi universitet revisionini yaratish",
        request=UniversityRevisionCreateSerializer,
        responses={
            201: UniversityRevisionListSerializer,
            400: OpenApiResponse(description="Invalid input."),
            401: OpenApiResponse(description="Authentication required."),
            403: OpenApiResponse(description="Insufficient permissions."),
            404: OpenApiResponse(description="University not found."),
        },
    )
    def post(self, request, university_id):
        serializer = UniversityRevisionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            revision = UniversityRevisionService.create_revision(
                actor=request.user,
                university_id=university_id,
                **serializer.validated_data,
            )
        except DjangoValidationError as exc:
            handle_service_validation_error(exc)
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc

        return Response(
            UniversityRevisionListSerializer(revision).data,
            status=status.HTTP_201_CREATED,
        )




class UniversityRevisionDetailAPIView(APIView):
    """Universitet revisionini ko'rish va tahrirlash API."""

    def get_permissions(self):
        permission_map = {
            "GET": CanViewUniversities,
            "PATCH": CanUpdateUniversity,
        }

        permission_class = permission_map.get(self.request.method)

        if permission_class is None:
            return super().get_permissions()

        return [permission_class()]

    @extend_schema(
        operation_id="retrieve_university_revision",
        tags=["Universities - Revisions"],
        summary="Universitet revisioni tafsilotlarini olish",
        responses={
            200: UniversityRevisionDetailSerializer,
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

        return Response(
            UniversityRevisionDetailSerializer(revision).data,
        )

    @extend_schema(
        operation_id="update_university_revision",
        tags=["Universities - Revisions"],
        summary="Universitet revisionini tahrirlash",
        request=UniversityRevisionUpdateSerializer,
        responses={
            200: UniversityRevisionDetailSerializer,
            400: OpenApiResponse(description="Invalid input or revision cannot be edited."),
            401: OpenApiResponse(description="Authentication required."),
            403: OpenApiResponse(description="Insufficient permissions."),
            404: OpenApiResponse(description="Revision not found."),
        },
    )
    def patch(self, request, revision_id):
        serializer = UniversityRevisionUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            revision = UniversityRevisionService.update_revision(
                actor=request.user,
                revision_id=revision_id,
                **serializer.validated_data,
            )
        except DjangoValidationError as exc:
            handle_service_validation_error(exc)
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc

        return Response(
            UniversityRevisionDetailSerializer(revision).data,
            status=status.HTTP_200_OK,
        )




class UniversityRevisionSubmitAPIView(APIView):
    """Revisionni ko'rib chiqishga yuborish API."""

    permission_classes = [CanSubmitUniversityForReview]

    @extend_schema(
        operation_id="submit_university_revision",
        tags=["Universities - Revisions"],
        summary="Revisionni ko'rib chiqishga yuborish",
        responses={
            200: UniversityRevisionDetailSerializer,
            400: OpenApiResponse(
                description="Revision cannot be submitted."
            ),
            401: OpenApiResponse(description="Authentication required."),
            403: OpenApiResponse(description="Insufficient permissions."),
            404: OpenApiResponse(description="Revision not found."),
        },
    )
    def post(self, request, revision_id):
        try:
            revision = UniversityRevisionService.submit_for_review(
                actor=request.user,
                revision_id=revision_id,
            )
        except DjangoValidationError as exc:
            handle_service_validation_error(exc)
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc

        return Response(
            UniversityRevisionDetailSerializer(revision).data,
            status=status.HTTP_200_OK,
        )




class UniversityRevisionApproveAPIView(APIView):
    """Universitet revisionini tasdiqlash API."""

    permission_classes = [CanApproveUniversity]

    @extend_schema(
        operation_id="approve_university_revision",
        tags=["Universities - Revisions"],
        summary="Universitet revisionini tasdiqlash",
        responses={
            200: UniversityRevisionDetailSerializer,
            400: OpenApiResponse(
                description="Revision cannot be approved."
            ),
            401: OpenApiResponse(description="Authentication required."),
            403: OpenApiResponse(description="Insufficient permissions."),
            404: OpenApiResponse(description="Revision not found."),
        },
    )
    def post(self, request, revision_id):
        try:
            revision = UniversityRevisionService.approve_revision(
                actor=request.user,
                revision_id=revision_id,
            )
        except DjangoValidationError as exc:
            handle_service_validation_error(exc)
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc

        return Response(
            UniversityRevisionDetailSerializer(revision).data,
            status=status.HTTP_200_OK,
        )




class UniversityRevisionRejectAPIView(APIView):
    """Universitet revisionini rad etish API."""

    permission_classes = [CanRejectUniversity]

    @extend_schema(
        operation_id="reject_university_revision",
        tags=["Universities - Revisions"],
        summary="Universitet revisionini rad etish",
        request=UniversityRevisionRejectSerializer,
        responses={
            200: UniversityRevisionDetailSerializer,
            400: OpenApiResponse(
                description="Invalid reason or revision cannot be rejected."
            ),
            401: OpenApiResponse(description="Authentication required."),
            403: OpenApiResponse(description="Insufficient permissions."),
            404: OpenApiResponse(description="Revision not found."),
        },
    )
    def post(self, request, revision_id):
        serializer = UniversityRevisionRejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            revision = UniversityRevisionService.reject_revision(
                actor=request.user,
                revision_id=revision_id,
                reason=serializer.validated_data["reason"],
            )
        except DjangoValidationError as exc:
            handle_service_validation_error(exc)
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc

        return Response(
            UniversityRevisionDetailSerializer(revision).data,
            status=status.HTTP_200_OK,
        )



class UniversityRevisionPublishAPIView(APIView):
    """Universitet revisionini ommaga nashr qilish API."""

    permission_classes = [CanPublishUniversity]

    @extend_schema(
        operation_id="publish_university_revision",
        tags=["Universities - Revisions"],
        summary="Universitet revisionini nashr qilish",
        description=(
            "Tasdiqlangan universitet revisionini ommaga nashr qiladi. "
            "Avvalgi published revision avtomatik arxivlanadi. "
            "Universitetda kamida bitta published Uzbek tarjimasi bo‘lishi shart."
        ),
        responses={
            200: UniversityRevisionDetailSerializer,
            400: OpenApiResponse(
                description="Revision cannot be published."
            ),
            401: OpenApiResponse(description="Authentication required."),
            403: OpenApiResponse(description="Insufficient permissions."),
            404: OpenApiResponse(description="Revision not found."),
        },
    )
    def post(self, request, revision_id):
        try:
            revision = UniversityRevisionService.publish_revision(
                actor=request.user,
                revision_id=revision_id,
            )
        except DjangoValidationError as exc:
            handle_service_validation_error(exc)
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc

        return Response(
            UniversityRevisionDetailSerializer(revision).data,
            status=status.HTTP_200_OK,
        )

