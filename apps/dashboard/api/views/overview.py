from drf_spectacular.utils import extend_schema
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from apps.dashboard.api.permissions import CanViewDashboard
from apps.dashboard.api.serializers.overview import (
    DashboardOverviewSerializer,
)
from apps.dashboard.services.dashboard_service import (
    get_dashboard_overview,
)


class DashboardOverviewAPIView(GenericAPIView):
    permission_classes = [CanViewDashboard]
    serializer_class = DashboardOverviewSerializer

    @extend_schema(
        operation_id="dashboard_overview",
        summary="Dashboard overview",
        description=(
            "Returns aggregated statistics for inquiries, admissions, "
            "universities, and programs. "
            "Accessible to superusers and users with the "
            "`dashboard.view_dashboard` permission."
        ),
        responses={
            200: DashboardOverviewSerializer,
        },
        tags=["Dashboard"],
    )
    def get(self, request, *args, **kwargs):
        data = get_dashboard_overview()
        serializer = self.get_serializer(data)

        return Response(serializer.data)