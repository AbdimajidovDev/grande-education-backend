from rest_framework.response import Response
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
)
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny
from rest_framework.exceptions import ValidationError
from rest_framework.serializers import Serializer, ListField, UUIDField

from apps.directions.models import DirectionTranslation
from apps.directions.selectors import get_public_directions
from apps.directions.api.serializers import DirectionPublicSerializer


class DirectionPublicListSerializer(Serializer):
    items = DirectionPublicSerializer(many=True)


class DirectionPublicListView(ListAPIView):
    serializer_class = DirectionPublicSerializer
    permission_classes = [AllowAny]
    pagination_class = None

    def get_language_code(self):
        language_code = self.request.query_params.get("lang", "uz")

        allowed_languages = DirectionTranslation.Language.values

        if language_code not in allowed_languages:
            raise ValidationError({
                "lang": (
                    f"Unsupported language. "
                    f"Allowed values: {', '.join(allowed_languages)}"
                )
            })

        return language_code

    def get_queryset(self):
        language_code = self.get_language_code()

        return get_public_directions(
            language_code=language_code,
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["language_code"] = self.get_language_code()
        return context

    @extend_schema(
        tags=["Directions - Public"],
        summary="Get public directions",
        description=(
            "Returns active directions with translations. "
            "If the requested translation is unavailable, "
            "Uzbek translation is used as fallback. "
            "Directions without either translation are excluded."
        ),
        parameters=[
            OpenApiParameter(
                name="lang",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Language code: uz, ru, en, zh, ja, de.",
                enum=DirectionTranslation.Language.values,
            ),
        ],
        responses={
            200: DirectionPublicListSerializer,
            400: OpenApiResponse(
                description="Unsupported language code."
            ),
        },
    )
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        serializer = self.get_serializer(
            queryset,
            many=True,
        )

        return Response({"items": serializer.data})
