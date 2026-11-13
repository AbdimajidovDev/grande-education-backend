
from rest_framework import generics
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.utils import (
    extend_schema,
    OpenApiParameter,
    OpenApiTypes,
)

from apps.site_settings.selectors import (
    get_public_site_stats,
    resolve_site_stat_translation,
    get_public_contact_office,
)

from apps.site_settings.api.serializers import (
    SiteStatPublicSerializer,
    ContactPublicSerializer,
)


class PublicSiteStatListView(generics.ListAPIView):
    serializer_class = SiteStatPublicSerializer
    permission_classes = [AllowAny]
    authentication_classes = []

    def get_queryset(self):
        language_code = self.request.query_params.get("lang", "uz")

        supported_languages = {
            "uz", "ru", "en", "zh", "ja", "de",
        }

        if language_code not in supported_languages:
            language_code = "uz"

        return get_public_site_stats(
            language_code=language_code,
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()

        language_code = self.request.query_params.get("lang", "uz")

        if language_code not in {"uz", "ru", "en", "zh", "ja", "de"}:
            language_code = "uz"

        context["language_code"] = language_code
        return context

    @extend_schema(
        tags=["Public — Site Settings"],
        summary="Get public site statistics",
        description=(
            "Returns active site statistics with translations. "
            "Falls back to Uzbek when the requested translation "
            "is unavailable."
        ),
        parameters=[
            OpenApiParameter(
                name="lang",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                enum=["uz", "ru", "en", "zh", "ja", "de"],
                description="Requested language code.",
            ),
        ],
        responses={
            200: SiteStatPublicSerializer(many=True),
        },
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class PublicContactView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        tags=["Public — Site Settings"],
        summary="Get public contact information",
        description=(
            "Returns contact information for the active main office, "
            "including phone, email, social links, address and "
            "working hours."
        ),
        responses={
            200: ContactPublicSerializer,
        },
    )
    def get(self, request, *args, **kwargs):
        office = get_public_contact_office()

        if office is None:
            return Response(
                {
                    "detail": "Contact information is not configured."
                },
                status=503,
            )

        serializer = ContactPublicSerializer(office)

        return Response(serializer.data)
