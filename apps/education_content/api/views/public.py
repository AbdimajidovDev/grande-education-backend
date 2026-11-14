from rest_framework import serializers
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.education_content.models.hybrid_teacher_translation import Language

from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
)

from apps.education_content.models import (
    HybridTeacherTranslation,
    LearningComponentTranslation,
    UniversityStepPageTranslation,
)
from apps.education_content.selectors import (
    get_public_hybrid_teachers,
    get_public_learning_components,
    get_public_university_step_page,
)
from apps.education_content.api.serializers import (
    HybridTeacherPublicSerializer,
    LearningComponentPublicSerializer,
    UniversityStepPagePublicSerializer,
)


class PublicLanguageMixin:
    def get_language_code(self, allowed_languages):
        language_code = self.request.query_params.get("lang", "uz")

        if language_code not in allowed_languages:
            raise ValidationError({
                "lang": (
                    f"Unsupported language. "
                    f"Allowed values: {', '.join(allowed_languages)}"
                )
            })

        return language_code

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["language_code"] = self.get_language_code(
            self.allowed_languages
        )
        return context


class HybridTeacherPublicListSerializer(serializers.Serializer):
    items = HybridTeacherPublicSerializer(many=True)


class LearningComponentPublicListSerializer(serializers.Serializer):
    items = LearningComponentPublicSerializer(many=True)


class PublicHybridTeacherListView(PublicLanguageMixin, ListAPIView):
    serializer_class = HybridTeacherPublicSerializer
    permission_classes = [AllowAny]
    authentication_classes = []
    pagination_class = None

    allowed_languages = Language.values

    def get_queryset(self):
        return get_public_hybrid_teachers(
            language_code=self.get_language_code(self.allowed_languages)
        )

    @extend_schema(
        tags=["Education Content - Public"],
        summary="Get public hybrid teachers",
        description=(
            "Returns active hybrid teachers with translated content. "
            "If the requested translation is unavailable, Uzbek is used "
            "as fallback. Teachers without either translation are excluded."
        ),
        parameters=[
            OpenApiParameter(
                name="lang",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Language code: uz, ru, en, zh, ja, de.",
                enum=Language.values
            ),
        ],
        responses={
            200: HybridTeacherPublicListSerializer,
            400: OpenApiResponse(description="Unsupported language code."),
        },
    )
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)

        return Response({"items": serializer.data})


class PublicLearningComponentListView(
    PublicLanguageMixin,
    ListAPIView,
):
    serializer_class = LearningComponentPublicSerializer
    permission_classes = [AllowAny]
    authentication_classes = []
    pagination_class = None

    allowed_languages = Language.values

    def get_queryset(self):
        return get_public_learning_components(
            language_code=self.get_language_code(self.allowed_languages)
        )

    @extend_schema(
        tags=["Education Content - Public"],
        summary="Get public learning components",
        description=(
            "Returns active learning components with translated content. "
            "If the requested translation is unavailable, Uzbek is used "
            "as fallback. Components without either translation are excluded."
        ),
        parameters=[
            OpenApiParameter(
                name="lang",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Language code: uz, ru, en, zh, ja, de.",
                enum=Language.values,            ),
        ],
        responses={
            200: LearningComponentPublicListSerializer,
            400: OpenApiResponse(description="Unsupported language code."),
        },
    )
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)

        return Response({"items": serializer.data})


class PublicUniversityStepPageView(PublicLanguageMixin, APIView,):
    permission_classes = [AllowAny]
    authentication_classes = []

    allowed_languages = Language.values

    @extend_schema(
        tags=["Education Content - Public"],
        summary="Get university step page",
        description=(
            "Returns the active university step page and its active steps. "
            "Uses the requested language, falling back to Uzbek. "
            "Returns 404 if no active page with an available translation exists."
        ),
        parameters=[
            OpenApiParameter(
                name="lang",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Language code: uz, ru, en, zh, ja, de.",
                enum=Language.values
            ),
        ],
        responses={
            200: UniversityStepPagePublicSerializer,
            400: OpenApiResponse(description="Unsupported language code."),
            404: OpenApiResponse(description="Active page not found."),
        },
    )
    def get(self, request, *args, **kwargs):
        language_code = self.get_language_code(self.allowed_languages)

        page = get_public_university_step_page(
            language_code=language_code
        )

        if page is None:
            raise NotFound("University step page not found.")

        serializer = UniversityStepPagePublicSerializer(
            page,
            context={
                "request": request,
                "language_code": language_code,
            },
        )

        return Response(serializer.data)