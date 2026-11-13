
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
)
from rest_framework import generics
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny

from apps.programs.api.serializers import ProgramPublicSerializer
from apps.programs.models import ProgramTranslation
from apps.programs.services.program_service import get_public_programs


@extend_schema(
    tags=["Public Programs"],
    summary="Get published programs",
    description=(
        "Returns published programs in the requested language. "
        "If a translation is unavailable, Uzbek translation is used."
    ),
    parameters=[
        OpenApiParameter(
            name="lang",
            type=str,
            location=OpenApiParameter.QUERY,
            required=False,
            description="Language code: uz, ru, en, zh, ja, de.",
            enum=ProgramTranslation.Language.values,
        ),
    ],
    responses={
        200: ProgramPublicSerializer(many=True),
        400: OpenApiResponse(
            description="Unsupported language code."
        ),
    },
)
class PublicProgramListView(generics.ListAPIView):
    serializer_class = ProgramPublicSerializer
    permission_classes = [AllowAny]
    pagination_class = None

    def get_language_code(self):
        language_code = self.request.query_params.get("lang", "uz")

        if language_code not in ProgramTranslation.Language.values:
            raise ValidationError({
                "lang": "Unsupported language code."
            })

        return language_code

    def get_queryset(self):
        return get_public_programs(self.get_language_code())

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["language_code"] = self.get_language_code()
        return context
