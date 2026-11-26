
from django.core.exceptions import (
    PermissionDenied as DjangoPermissionDenied,
    ValidationError as DjangoValidationError,
)

from rest_framework import status
from rest_framework.exceptions import (
    NotFound,
    PermissionDenied,
    ValidationError,
)
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.utils import extend_schema, OpenApiResponse

from apps.universities.models import FAQ, FAQTranslation
from apps.universities.api.permissions import (
    CanViewFAQs,
    CanCreateFAQ,
    CanUpdateFAQ,
    CanSubmitFAQForReview,
    CanApproveFAQ,
    CanRejectFAQ,
    CanPublishFAQ,
    CanDeleteFAQ,
    CanViewFAQTranslations,
    CanDeleteFAQTranslation,
    CanDeleteFAQRevision,
)
from apps.universities.api.cms.serializers.faq_serializers import (
    FAQCreateSerializer,
    FAQUpdateSerializer,
    FAQListSerializer,
    FAQTranslationCreateSerializer,
    FAQTranslationListSerializer,
    FAQRevisionCreateSerializer,
    FAQRevisionUpdateSerializer,
    FAQRevisionListSerializer,
)
from apps.universities.selectors.faq_selector import FAQSelector
from apps.universities.services.exceptions import ResourceNotFoundError
from apps.universities.services.faq_service import FAQService
from apps.universities.services.faq_translation_service import (
    FAQTranslationService,
)


def handle_service_exception(exc):
    """Service exceptionlarini DRF exceptionlariga aylantiradi."""

    if isinstance(exc, ResourceNotFoundError):
        raise NotFound(str(exc)) from exc

    if isinstance(exc, DjangoValidationError):
        if hasattr(exc, "message_dict"):
            raise ValidationError(exc.message_dict) from exc

        raise ValidationError(exc.messages) from exc

    if isinstance(exc, DjangoPermissionDenied):
        raise PermissionDenied(str(exc)) from exc

    raise exc


class FAQListCreateAPIView(APIView):
    """FAQ ro'yxati va yangi FAQ yaratish."""

    def get_permissions(self):
        if self.request.method == "GET":
            return [CanViewFAQs()]
        return [CanCreateFAQ()]

    @extend_schema(
        operation_id="list_faqs",
        tags=["CMS - FAQ"],
        summary="FAQ ro'yxatini olish",
        responses={200: FAQListSerializer(many=True)},
    )
    def get(self, request):
        faqs = FAQSelector.get_faq_queryset()

        return Response(
            FAQListSerializer(faqs, many=True).data,
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        operation_id="create_faq",
        tags=["CMS - FAQ"],
        summary="Yangi FAQ yaratish",
        request=FAQCreateSerializer,
        responses={201: FAQListSerializer},
    )
    def post(self, request):
        serializer = FAQCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            faq = FAQService.create_faq(
                actor=request.user,
                **serializer.validated_data,
            )
        except (DjangoValidationError, DjangoPermissionDenied) as exc:
            handle_service_exception(exc)

        return Response(
            FAQListSerializer(faq).data,
            status=status.HTTP_201_CREATED,
        )


class FAQDetailAPIView(APIView):
    """Bitta FAQ ma'lumotlarini olish, yangilash va o'chirish."""

    def get_permissions(self):
        permission_map = {
            "GET": CanViewFAQs,
            "PATCH": CanUpdateFAQ,
            "DELETE": CanDeleteFAQ,
        }
        permission_class = permission_map.get(self.request.method)
        if permission_class is None:
            return super().get_permissions()
        return [permission_class()]

    @extend_schema(
        operation_id="retrieve_faq",
        tags=["CMS - FAQ"],
        summary="FAQ ma'lumotlarini olish",
        responses={200: FAQListSerializer},
    )
    def get(self, request, faq_id):
        faq = FAQSelector.get_faq_by_id(faq_id)

        if faq is None:
            raise NotFound("FAQ topilmadi.")

        return Response(
            FAQListSerializer(faq).data,
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        operation_id="update_faq",
        tags=["CMS - FAQ"],
        summary="FAQ ma'lumotlarini yangilash",
        request=FAQUpdateSerializer,
        responses={200: FAQListSerializer},
    )
    def patch(self, request, faq_id):
        serializer = FAQUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            faq = FAQService.update_faq(
                actor=request.user,
                faq_id=faq_id,
                **serializer.validated_data,
            )
        except (DjangoValidationError, DjangoPermissionDenied) as exc:
            handle_service_exception(exc)

        return Response(
            FAQListSerializer(faq).data,
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        operation_id="delete_faq",
        tags=["CMS - FAQ"],
        summary="Arxivlangan FAQni o'chirish",
        description=(
            "Faqat faolsizlantirilgan (is_active=False) va barcha tarjima "
            "reviziyalari ARCHIVED holatida bo'lgan FAQni o'chiradi. "
            "Talab qilinadigan permission: universities.delete_faq."
        ),
        responses={
            204: OpenApiResponse(description="FAQ deleted."),
            401: OpenApiResponse(description="Authentication required."),
            403: OpenApiResponse(description="Insufficient permissions."),
            404: OpenApiResponse(description="FAQ not found."),
            422: OpenApiResponse(description="FAQ cannot be deleted."),
        },
    )
    def delete(self, request, faq_id):
        try:
            FAQService.delete_faq(
                actor=request.user,
                faq_id=faq_id,
            )
        except (
            ResourceNotFoundError,
            DjangoValidationError,
            DjangoPermissionDenied,
        ) as exc:
            handle_service_exception(exc)

        return Response(status=status.HTTP_204_NO_CONTENT)


class FAQTranslationListCreateAPIView(APIView):
    """FAQ tarjimalarini olish va yangi tarjima yaratish."""

    def get_permissions(self):
        if self.request.method == "GET":
            return [CanViewFAQTranslations()]
        return [CanCreateFAQ()]

    @extend_schema(
        operation_id="list_faq_translations",
        tags=["CMS - FAQ"],
        summary="FAQ tarjimalarini olish",
        responses={200: FAQTranslationListSerializer(many=True)},
    )
    def get(self, request, faq_id):
        if FAQSelector.get_faq_by_id(faq_id) is None:
            raise NotFound("FAQ topilmadi.")

        translations = FAQSelector.get_translations_by_faq(faq_id)

        return Response(
            FAQTranslationListSerializer(
                translations,
                many=True,
            ).data,
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        operation_id="create_faq_translation",
        tags=["CMS - FAQ"],
        summary="FAQ tarjimasini yaratish",
        request=FAQTranslationCreateSerializer,
        responses={201: FAQTranslationListSerializer},
    )
    def post(self, request, faq_id):
        serializer = FAQTranslationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            translation = FAQTranslationService.create_translation(
                actor=request.user,
                faq_id=faq_id,
                **serializer.validated_data,
            )
        except (DjangoValidationError, DjangoPermissionDenied) as exc:
            handle_service_exception(exc)

        return Response(
            FAQTranslationListSerializer(translation).data,
            status=status.HTTP_201_CREATED,
        )


class FAQTranslationDetailAPIView(APIView):
    """FAQ tarjimasini olish va o'chirish."""

    def get_permissions(self):
        permission_map = {
            "GET": CanViewFAQTranslations,
            "DELETE": CanDeleteFAQTranslation,
        }
        permission_class = permission_map.get(self.request.method)
        if permission_class is None:
            return super().get_permissions()
        return [permission_class()]

    @extend_schema(
        operation_id="retrieve_faq_translation",
        tags=["CMS - FAQ"],
        summary="FAQ tarjimasi ma'lumotlarini olish",
        responses={
            200: FAQTranslationListSerializer,
            401: OpenApiResponse(description="Authentication required."),
            403: OpenApiResponse(description="Insufficient permissions."),
            404: OpenApiResponse(description="FAQ translation not found."),
        },
    )
    def get(self, request, translation_id):
        translation = FAQSelector.get_translation_by_id(translation_id)

        if translation is None:
            raise NotFound("FAQ tarjimasi topilmadi.")

        return Response(
            FAQTranslationListSerializer(translation).data,
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        operation_id="delete_faq_translation",
        tags=["CMS - FAQ"],
        summary="Arxivlangan FAQ tarjimasini o'chirish",
        description=(
            "Faqat barcha reviziyalari ARCHIVED holatida bo'lgan (nashr qilinmagan) "
            "FAQ tarjimasini o'chiradi. "
            "Talab qilinadigan permission: universities.delete_faqtranslation."
        ),
        responses={
            204: OpenApiResponse(description="FAQ translation deleted."),
            401: OpenApiResponse(description="Authentication required."),
            403: OpenApiResponse(description="Insufficient permissions."),
            404: OpenApiResponse(description="FAQ translation not found."),
            422: OpenApiResponse(description="FAQ translation cannot be deleted."),
        },
    )
    def delete(self, request, translation_id):
        try:
            FAQTranslationService.delete_translation(
                actor=request.user,
                translation_id=translation_id,
            )
        except (
            ResourceNotFoundError,
            DjangoValidationError,
            DjangoPermissionDenied,
        ) as exc:
            handle_service_exception(exc)

        return Response(status=status.HTTP_204_NO_CONTENT)


class FAQRevisionListCreateAPIView(APIView):
    """Tarjima revisionlarini olish va yangi revision yaratish."""

    def get_permissions(self):
        if self.request.method == "GET":
            return [CanViewFAQs()]
        return [CanUpdateFAQ()]

    @extend_schema(
        operation_id="list_faq_revisions",
        tags=["CMS - FAQ"],
        summary="FAQ tarjimasi revisionlari tarixini olish",
        responses={200: FAQRevisionListSerializer(many=True)},
    )
    def get(self, request, translation_id):
        translation = FAQSelector.get_translation_by_id(translation_id)

        if translation is None:
            raise NotFound("FAQ tarjimasi topilmadi.")

        revisions = FAQSelector.get_revisions_by_translation(
            translation_id
        )

        return Response(
            FAQRevisionListSerializer(revisions, many=True).data,
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        operation_id="create_faq_revision",
        tags=["CMS - FAQ"],
        summary="Yangi FAQ revision yaratish",
        request=FAQRevisionCreateSerializer,
        responses={201: FAQRevisionListSerializer},
    )
    def post(self, request, translation_id):
        serializer = FAQRevisionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            revision = FAQTranslationService.create_revision(
                actor=request.user,
                translation_id=translation_id,
                **serializer.validated_data,
            )
        except (DjangoValidationError, DjangoPermissionDenied) as exc:
            handle_service_exception(exc)

        return Response(
            FAQRevisionListSerializer(revision).data,
            status=status.HTTP_201_CREATED,
        )


class FAQRevisionDetailAPIView(APIView):
    """FAQ revisionini olish, DRAFT holatida tahrirlash va o'chirish."""

    def get_permissions(self):
        permission_map = {
            "GET": CanViewFAQs,
            "PATCH": CanUpdateFAQ,
            "DELETE": CanDeleteFAQRevision,
        }
        permission_class = permission_map.get(self.request.method)
        if permission_class is None:
            return super().get_permissions()
        return [permission_class()]

    @extend_schema(
        operation_id="retrieve_faq_revision",
        tags=["CMS - FAQ"],
        summary="FAQ revision ma'lumotlarini olish",
        responses={200: FAQRevisionListSerializer},
    )
    def get(self, request, revision_id):
        revision = FAQSelector.get_revision_by_id(revision_id)

        if revision is None:
            raise NotFound("FAQ revisioni topilmadi.")

        return Response(
            FAQRevisionListSerializer(revision).data,
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        operation_id="update_faq_revision",
        tags=["CMS - FAQ"],
        summary="FAQ revisionini tahrirlash",
        request=FAQRevisionUpdateSerializer,
        responses={200: FAQRevisionListSerializer},
    )
    def patch(self, request, revision_id):
        serializer = FAQRevisionUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            revision = FAQTranslationService.update_revision(
                actor=request.user,
                revision_id=revision_id,
                **serializer.validated_data,
            )
        except (DjangoValidationError, DjangoPermissionDenied) as exc:
            handle_service_exception(exc)

        return Response(
            FAQRevisionListSerializer(revision).data,
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        operation_id="delete_faq_revision",
        tags=["CMS - FAQ"],
        summary="ARCHIVED FAQ revisionini o'chirish",
        description=(
            "Faqat ARCHIVED holatidagi FAQ revisionini o'chiradi. "
            "Talab qilinadigan permission: universities.delete_faqtranslationrevision."
        ),
        responses={
            204: OpenApiResponse(description="FAQ revision deleted."),
            401: OpenApiResponse(description="Authentication required."),
            403: OpenApiResponse(description="Insufficient permissions."),
            404: OpenApiResponse(description="FAQ revision not found."),
            422: OpenApiResponse(description="FAQ revision cannot be deleted."),
        },
    )
    def delete(self, request, revision_id):
        try:
            FAQTranslationService.delete_revision(
                actor=request.user,
                revision_id=revision_id,
            )
        except (
            ResourceNotFoundError,
            DjangoValidationError,
            DjangoPermissionDenied,
        ) as exc:
            handle_service_exception(exc)

        return Response(status=status.HTTP_204_NO_CONTENT)


class FAQRevisionWorkflowAPIView(APIView):
    """FAQ revisionining REVIEW, APPROVE, REJECT va PUBLISH amallari."""

    def get_permissions(self):
        action = self.kwargs.get("action")
        permission_map = {
            "submit": CanSubmitFAQForReview,
            "approve": CanApproveFAQ,
            "reject": CanRejectFAQ,
            "publish": CanPublishFAQ,
        }
        permission_class = permission_map.get(action, CanUpdateFAQ)
        return [permission_class()]

    @extend_schema(
        operation_id="change_faq_revision_workflow",
        tags=["CMS - FAQ"],
        summary="FAQ revisionining workflow holatini o'zgartirish",
        request=None,
        responses={
            200: FAQRevisionListSerializer,
            422: OpenApiResponse(description="Workflow validation error."),
        },
    )
    def post(self, request, revision_id, action):
        if action == "reject":
            reason = request.data.get("reason")

            if not isinstance(reason, str) or not reason.strip():
                raise ValidationError({
                    "reason": "Rad etish sababi kiritilishi shart."
                })

        methods = {
            "submit": FAQTranslationService.submit_for_review,
            "approve": FAQTranslationService.approve_revision,
            "reject": FAQTranslationService.reject_revision,
            "publish": FAQTranslationService.publish_translation_revision,
        }

        service_method = methods.get(action)

        if service_method is None:
            raise NotFound("Noma'lum workflow amali.")

        kwargs = {
            "actor": request.user,
            "revision_id": revision_id,
        }

        if action == "reject":
            kwargs["reason"] = reason

        try:
            revision = service_method(**kwargs)
        except (DjangoValidationError, DjangoPermissionDenied) as exc:
            handle_service_exception(exc)

        return Response(
            FAQRevisionListSerializer(revision).data,
            status=status.HTTP_200_OK,
        )


class FAQRevisionArchiveAPIView(APIView):
    """FAQ revisionini ARCHIVED holatiga o'tkazish API."""

    permission_classes = [CanUpdateFAQ]

    @extend_schema(
        operation_id="archive_faq_revision",
        tags=["CMS - FAQ"],
        summary="FAQ revisionini arxivlash",
        request=None,
        responses={
            200: FAQRevisionListSerializer,
            401: OpenApiResponse(description="Authentication required."),
            403: OpenApiResponse(description="Insufficient permissions."),
            404: OpenApiResponse(description="FAQ revision not found."),
            422: OpenApiResponse(description="FAQ revision cannot be archived."),
        },
    )
    def post(self, request, revision_id):
        try:
            revision = FAQTranslationService.archive_revision(
                actor=request.user,
                revision_id=revision_id,
            )
        except (
            ResourceNotFoundError,
            DjangoValidationError,
            DjangoPermissionDenied,
        ) as exc:
            handle_service_exception(exc)

        return Response(
            FAQRevisionListSerializer(revision).data,
            status=status.HTTP_200_OK,
        )

