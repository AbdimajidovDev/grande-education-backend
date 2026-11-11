
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.utils import extend_schema, OpenApiResponse

from apps.universities.api.public.serializers.admission_period_serializers import (
    PublicUniversityAdmissionPeriodSerializer,
)

from apps.universities.selectors.university_selector import UniversitySelector
from apps.universities.selectors.university_admission_period_selector import (
    UniversityAdmissionPeriodSelector,
)


class PublicUniversityAdmissionPeriodListAPIView(APIView):
    """Universitetning nashr qilingan qabul davrlari API."""

    authentication_classes = []
    permission_classes = []

    @extend_schema(
        operation_id="list_public_university_admission_periods",
        tags=["Public - Universities"],
        summary="Universitet qabul davrlarini olish",
        description=(
            "Faqat universitetning joriy PUBLISHED revisioniga "
            "tegishli qabul davrlarini qaytaradi."
        ),
        responses={
            200: PublicUniversityAdmissionPeriodSerializer(many=True),
            404: OpenApiResponse(description="University not found."),
        },
    )
    def get(self, request, slug):
        university, _ = UniversitySelector.get_public_university_by_slug(
            slug=slug,
            language_code=request.query_params.get("lang", "uz"),
        )

        if university is None:
            raise NotFound("Universitet topilmadi.")

        periods = (
            UniversityAdmissionPeriodSelector
            .get_public_periods_by_university(
                university_id=university.pk,
            )
        )

        serializer = PublicUniversityAdmissionPeriodSerializer(
            periods,
            many=True,
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )
