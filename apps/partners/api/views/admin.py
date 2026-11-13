
from rest_framework import status, viewsets
from rest_framework.parsers import (
    JSONParser,
    MultiPartParser,
    FormParser,
)
from rest_framework.permissions import DjangoModelPermissions
from rest_framework.response import Response

from apps.partners.api.serializers import PartnerAdminSerializer
from apps.partners.selectors import get_admin_partners
from apps.partners.services import (
    create_partner,
    update_partner,
    delete_partner,
)


class PartnerViewSet(viewsets.ModelViewSet):
    serializer_class = PartnerAdminSerializer
    permission_classes = [DjangoModelPermissions]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_queryset(self):
        return get_admin_partners()

    def perform_create(self, serializer):
        serializer.instance = create_partner(
            validated_data=serializer.validated_data,
        )

    def perform_update(self, serializer):
        self.instance = update_partner(
            partner=self.get_object(),
            validated_data=serializer.validated_data,
        )

    def perform_destroy(self, instance):
        delete_partner(partner=instance)

