
from rest_framework import generics

from rest_framework.permissions import AllowAny

from drf_spectacular.utils import (
    extend_schema,
    OpenApiResponse,
)

from apps.partners.api.serializers import PartnerPublicSerializer
from apps.partners.selectors import get_public_partners


class PublicPartnerListView(generics.ListAPIView):
    serializer_class = PartnerPublicSerializer
    permission_classes = [AllowAny]
    pagination_class = None

    @extend_schema(
        summary="Public partners list",
        description=(
            "Faqat faol hamkorlar ro'yxatini qaytaradi. "
            "Hamkorlar order va name bo'yicha tartiblanadi."
        ),
        tags=["Partners - Public"],
        responses={
            200: PartnerPublicSerializer(many=True),
        },
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        return get_public_partners()
