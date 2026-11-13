
from rest_framework import generics
from rest_framework.permissions import AllowAny

from apps.partners.api.serializers import PartnerPublicSerializer
from apps.partners.selectors import get_public_partners


class PublicPartnerListView(generics.ListAPIView):
    serializer_class = PartnerPublicSerializer
    permission_classes = [AllowAny]
    pagination_class = None

    def get_queryset(self):
        return get_public_partners()
