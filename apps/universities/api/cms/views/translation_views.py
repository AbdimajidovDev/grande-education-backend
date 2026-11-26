
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
    CanCreateUniversity,
    CanUpdateUniversity,
    CanViewUniversityTranslations,
    CanDeleteUniversityTranslation,
    CanDeleteUniversityTranslationRevision,
)
from apps.universities.api.cms.serializers.translation_serializers import (
    UniversityTranslationCreateSerializer,
    UniversityTranslationListSerializer,
)
from apps.universities.selectors.university_selector import UniversitySelector
from apps.universities.selectors.university_translation_selector import (
    UniversityTranslationSelector,
)
from apps.universities.services.exceptions import ResourceNotFoundError
from apps.universities.services.university_translation_service import (
    UniversityTranslationService,
)
from apps.universities.api.cms.serializers.translation_serializers import (
    UniversityTranslationRevisionCreateSerializer,
    UniversityTranslationRevisionDetailSerializer,
    UniversityTranslationRevisionUpdateSerializer
)
from apps.universities.api.permissions import (
    CanSubmitUniversityForReview,
    CanApproveUniversity,
    CanRejectUniversity,
    CanPublishUniversity,
)
from apps.universities.api.cms.serializers.translation_serializers import (
    UniversityTranslationRevisionRejectSerializer,
)


def handle_service_validation_error(exc):
    """Django ValidationError'ni DRF ValidationError'ga aylantiradi."""

    if hasattr(exc, "message_dict"):
        raise serializers.ValidationError(exc.message_dict)

    raise serializers.ValidationError(exc.messages)


class UniversityTranslationListCreateAPIView(APIView):
    """Universitet tarjimalarini ro'yxatlash va yaratish API."""

    pagination_class = StandardResultsPagination

    def get_permissions(self):
        permission_map = {
            "GET": CanViewUniversities,
            "POST": CanCreateUniversity,
        }

        permission_class = permission_map.get(self.request.method)

        if permission_class is None:
            return super().get_permissions()

        return [permission_class()]

    @extend_schema(
        operation_id="list_university_translations",
        tags=["Universities - Translations"],
        summary="Universitet tarjimalari ro'yxatini olish",
        responses={
            200: UniversityTranslationListSerializer(many=True),
            401: OpenApiResponse(description="Authentication required."),
            403: OpenApiResponse(description="Insufficient permissions."),
            404: OpenApiResponse(description="University not found."),
        },
    )
    def get(self, request, university_id):
        if UniversitySelector.get_university_by_id(university_id) is None:
            raise NotFound("Universitet topilmadi.")

        translations = (
            UniversityTranslationSelector.get_translations_by_university(
                university_id=university_id,
            )
        )

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(
            translations,
            request,
            view=self,
        )

        serializer = UniversityTranslationListSerializer(
            page,
            many=True,
        )

        return paginator.get_paginated_response(serializer.data)

    @extend_schema(
        operation_id="create_university_translation",
        tags=["Universities - Translations"],
        summary="Universitet uchun yangi tarjima yaratish",
        request=UniversityTranslationCreateSerializer,
        responses={
            201: UniversityTranslationListSerializer,
            400: OpenApiResponse(description="Invalid input."),
            401: OpenApiResponse(description="Authentication required."),
            403: OpenApiResponse(description="Insufficient permissions."),
        },
    )
    def post(self, request, university_id):
        serializer = UniversityTranslationCreateSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        try:
            translation = UniversityTranslationService.create_translation(
                actor=request.user,
                university_id=university_id,
                **serializer.validated_data,
            )
        except DjangoValidationError as exc:
            handle_service_validation_error(exc)
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc

        return Response(
            UniversityTranslationListSerializer(translation).data,
            status=status.HTTP_201_CREATED,
        )


class UniversityTranslationDetailAPIView(APIView):
    """Universitet tarjimasini ko'rish va o'chirish API."""

    def get_permissions(self):
        permission_map = {
            "GET": CanViewUniversityTranslations,
            "DELETE": CanDeleteUniversityTranslation,
        }

        permission_class = permission_map.get(self.request.method)

        if permission_class is None:
            return super().get_permissions()

        return [permission_class()]

    @extend_schema(
        operation_id="retrieve_university_translation",
        tags=["Universities - Translations"],
        summary="Universitet tarjimasi tafsilotlarini olish",
        responses={
            200: UniversityTranslationListSerializer,
            401: OpenApiResponse(description="Authentication required."),
            403: OpenApiResponse(description="Insufficient permissions."),
            404: OpenApiResponse(description="Translation not found."),
        },
    )
    def get(self, request, translation_id):
        translation = UniversityTranslationSelector.get_translation_by_id(
            translation_id=translation_id,
        )

        if translation is None:
            raise NotFound("Universitet tarjimasi topilmadi.")

        return Response(
            UniversityTranslationListSerializer(translation).data,
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        operation_id="delete_university_translation",
        tags=["Universities - Translations"],
        summary="Arxivlangan universitet tarjimasini o'chirish",
        description=(
            "Faqat barcha reviziyalari ARCHIVED holatida bo'lgan (nashr qilinmagan) "
            "universitet tarjimasini o'chiradi. "
            "Talab qilinadigan permission: universities.delete_universitytranslation."
        ),
        responses={
            204: OpenApiResponse(description="Translation deleted."),
            401: OpenApiResponse(description="Authentication required."),
            403: OpenApiResponse(description="Insufficient permissions."),
            404: OpenApiResponse(description="Translation not found."),
            422: OpenApiResponse(description="Translation cannot be deleted."),
        },
    )
    def delete(self, request, translation_id):
        try:
            UniversityTranslationService.delete_translation(
                actor=request.user,
                translation_id=translation_id,
            )
        except ResourceNotFoundError as exc:
            raise NotFound(str(exc)) from exc
        except DjangoValidationError as exc:
            handle_service_validation_error(exc)
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc

        return Response(status=status.HTTP_204_NO_CONTENT)





class UniversityTranslationRevisionListCreateAPIView(APIView):
    pagination_class = StandardResultsPagination

    def get_permissions(self):
        if self.request.method == "GET":
            return [CanViewUniversities()]

        return [CanUpdateUniversity()]

    @extend_schema(
        tags=["CMS - University Translations"],
        responses={200: UniversityTranslationRevisionDetailSerializer(many=True)},
    )
    def get(self, request, translation_id):
        # Translation mavjudligini tekshirish
        translation = UniversityTranslationSelector.get_translation_by_id(
            translation_id=translation_id
        )

        if not translation:
            raise NotFound("Translation topilmadi.")

        queryset = UniversityTranslationSelector.get_revisions_by_translation(
            translation_id=translation_id
        )

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)

        serializer = UniversityTranslationRevisionDetailSerializer(
            page,
            many=True,
        )

        return paginator.get_paginated_response(serializer.data)

    @extend_schema(
        tags=["CMS - University Translations"],
        request=UniversityTranslationRevisionCreateSerializer,
        responses={201: UniversityTranslationRevisionDetailSerializer},
    )
    def post(self, request, translation_id):
        serializer = UniversityTranslationRevisionCreateSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

        try:
            revision = UniversityTranslationService.create_revision(
                actor=request.user,
                translation_id=translation_id,
                **serializer.validated_data,
            )
        except DjangoValidationError as exc:
            raise handle_service_validation_error(exc)
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc))

        response_serializer = UniversityTranslationRevisionDetailSerializer(
            revision
        )

        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
        )



class UniversityTranslationRevisionDetailAPIView(APIView):

    def get_permissions(self):
        permission_map = {
            "GET": CanViewUniversities,
            "PATCH": CanUpdateUniversity,
            "DELETE": CanDeleteUniversityTranslationRevision,
        }

        permission_class = permission_map.get(self.request.method)

        if permission_class is None:
            return super().get_permissions()

        return [permission_class()]

    @extend_schema(
        tags=["CMS - University Translations"],
        responses={200: UniversityTranslationRevisionDetailSerializer},
    )
    def get(self, request, revision_id):
        revision = UniversityTranslationSelector.get_revision_by_id(
            revision_id=revision_id
        )

        if not revision:
            raise NotFound("Translation revision topilmadi.")

        serializer = UniversityTranslationRevisionDetailSerializer(revision)

        return Response(serializer.data)

    @extend_schema(
        tags=["CMS - University Translations"],
        request=UniversityTranslationRevisionUpdateSerializer,
        responses={200: UniversityTranslationRevisionDetailSerializer},
    )
    def patch(self, request, revision_id):
        serializer = UniversityTranslationRevisionUpdateSerializer(
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)

        try:
            revision = UniversityTranslationService.update_revision(
                actor=request.user,
                revision_id=revision_id,
                **serializer.validated_data,
            )
        except DjangoValidationError as exc:
            raise handle_service_validation_error(exc)
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc))

        response_serializer = UniversityTranslationRevisionDetailSerializer(
            revision
        )

        return Response(response_serializer.data)

    @extend_schema(
        operation_id="delete_university_translation_revision",
        tags=["CMS - University Translations"],
        summary="ARCHIVED tarjima revisionini o'chirish",
        description=(
            "Faqat ARCHIVED holatidagi tarjima revisionini o'chiradi. "
            "Talab qilinadigan permission: universities.delete_universitytranslationrevision."
        ),
        responses={
            204: OpenApiResponse(description="Translation revision deleted."),
            401: OpenApiResponse(description="Authentication required."),
            403: OpenApiResponse(description="Insufficient permissions."),
            404: OpenApiResponse(description="Translation revision not found."),
            422: OpenApiResponse(description="Translation revision cannot be deleted."),
        },
    )
    def delete(self, request, revision_id):
        try:
            UniversityTranslationService.delete_revision(
                actor=request.user,
                revision_id=revision_id,
            )
        except ResourceNotFoundError as exc:
            raise NotFound(str(exc)) from exc
        except DjangoValidationError as exc:
            handle_service_validation_error(exc)
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc

        return Response(status=status.HTTP_204_NO_CONTENT)



class UniversityTranslationRevisionSubmitAPIView(APIView):
    permission_classes = [CanSubmitUniversityForReview]

    @extend_schema(tags=["CMS - University Translations"])
    def post(self, request, revision_id):
        try:
            revision = UniversityTranslationService.submit_for_review(
                actor=request.user,
                revision_id=revision_id,
            )
        except DjangoValidationError as exc:
            raise handle_service_validation_error(exc)
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc))

        serializer = UniversityTranslationRevisionDetailSerializer(revision)
        return Response(serializer.data)


class UniversityTranslationRevisionApproveAPIView(APIView):
    permission_classes = [CanApproveUniversity]

    @extend_schema(tags=["CMS - University Translations"])
    def post(self, request, revision_id):
        try:
            revision = UniversityTranslationService.approve_revision(
                actor=request.user,
                revision_id=revision_id,
            )
        except DjangoValidationError as exc:
            raise handle_service_validation_error(exc)
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc))

        serializer = UniversityTranslationRevisionDetailSerializer(revision)
        return Response(serializer.data)


class UniversityTranslationRevisionRejectAPIView(APIView):
    permission_classes = [CanRejectUniversity]

    @extend_schema(
        tags=["CMS - University Translations"],
        request=UniversityTranslationRevisionRejectSerializer,
    )
    def post(self, request, revision_id):
        serializer = UniversityTranslationRevisionRejectSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

        try:
            revision = UniversityTranslationService.reject_revision(
                actor=request.user,
                revision_id=revision_id,
                reason=serializer.validated_data["reason"],
            )
        except DjangoValidationError as exc:
            raise handle_service_validation_error(exc)
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc))

        response_serializer = UniversityTranslationRevisionDetailSerializer(
            revision
        )
        return Response(response_serializer.data)


class UniversityTranslationRevisionPublishAPIView(APIView):
    permission_classes = [CanPublishUniversity]

    @extend_schema(tags=["CMS - University Translations"])
    def post(self, request, revision_id):
        try:
            revision = (
                UniversityTranslationService.publish_translation_revision(
                    actor=request.user,
                    revision_id=revision_id,
                )
            )
        except DjangoValidationError as exc:
            raise handle_service_validation_error(exc)
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc))

        serializer = UniversityTranslationRevisionDetailSerializer(revision)
        return Response(serializer.data)


class UniversityTranslationRevisionArchiveAPIView(APIView):
    """Tarjima revisionini ARCHIVED holatiga o'tkazish API."""

    permission_classes = [CanUpdateUniversity]

    @extend_schema(
        operation_id="archive_university_translation_revision",
        tags=["CMS - University Translations"],
        summary="Tarjima revisionini arxivlash",
        request=None,
        responses={
            200: UniversityTranslationRevisionDetailSerializer,
            401: OpenApiResponse(description="Authentication required."),
            403: OpenApiResponse(description="Insufficient permissions."),
            404: OpenApiResponse(description="Translation revision not found."),
            422: OpenApiResponse(description="Translation revision cannot be archived."),
        },
    )
    def post(self, request, revision_id):
        try:
            revision = UniversityTranslationService.archive_revision(
                actor=request.user,
                revision_id=revision_id,
            )
        except ResourceNotFoundError as exc:
            raise NotFound(str(exc)) from exc
        except DjangoValidationError as exc:
            handle_service_validation_error(exc)
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc

        return Response(
            UniversityTranslationRevisionDetailSerializer(revision).data,
            status=status.HTTP_200_OK,
        )

