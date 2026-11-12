
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.utils import extend_schema, OpenApiResponse

from apps.inquiries.api.public.serializers import (
    InquiryCategorySerializer,
)
from apps.inquiries.selectors.category_selector import (
    get_active_inquiry_categories,
)


class PublicInquiryCategoryListAPIView(APIView):
    """Ariza kategoriyalarini tanlangan tilda olish."""

    authentication_classes = []
    permission_classes = []

    @extend_schema(
        operation_id="list_public_inquiry_categories",
        tags=["Public - Inquiries"],
        summary="Ariza kategoriyalarini olish",
        description=(
            "Faol ariza kategoriyalarini tanlangan tilda qaytaradi. "
            "Tarjima mavjud bo'lmasa, o'zbekcha tarjimadan foydalanadi."
        ),
        responses={
            200: InquiryCategorySerializer(many=True),
            500: OpenApiResponse(
                description="Internal server error."
            ),
        },
    )
    def get(self, request):
        language_code = request.query_params.get(
            "lang",
            "uz",
        ).strip().lower()

        if not language_code:
            language_code = "uz"

        categories = get_active_inquiry_categories(
            language_code=language_code,
        )

        serializer = InquiryCategorySerializer(
            categories,
            many=True,
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )
