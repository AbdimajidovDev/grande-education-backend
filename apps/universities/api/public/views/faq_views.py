
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.utils import extend_schema, OpenApiResponse

from apps.universities.constants import SUPPORTED_LANGUAGES
from apps.universities.api.public.serializers.faq_serializers import (
    PublicFAQSerializer,
)
from apps.universities.selectors.faq_selector import FAQSelector


class PublicFAQListAPIView(APIView):
    """Public FAQ savol-javoblarini olish."""

    authentication_classes = []
    permission_classes = []

    @extend_schema(
        operation_id="list_public_faqs",
        tags=["Public - FAQ"],
        summary="FAQ savol-javoblarini olish",
        description=(
            "Faqat faol FAQ va tanlangan tildagi PUBLISHED "
            "revisionlarni qaytaradi."
        ),
        responses={
            200: PublicFAQSerializer(many=True),
            400: OpenApiResponse(
                description="Qo'llab-quvvatlanmaydigan til kodi."
            ),
        },
    )
    def get(self, request):
        language_code = request.query_params.get(
            "lang",
            "uz",
        ).strip().lower()

        if language_code not in SUPPORTED_LANGUAGES:
            raise ValidationError({
                "lang": "Qo'llab-quvvatlanmaydigan til kodi."
            })

        faqs = FAQSelector.get_public_faqs(language_code)

        serializer = PublicFAQSerializer(
            faqs,
            many=True,
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )
