from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from drf_spectacular.utils import extend_schema

from apps.common.pagination import StandardResultsPagination
from apps.universities.selectors.university_selector import UniversitySelector
from apps.universities.api.public.serializers.public_serializers import (
    PublicUniversityListSerializer,
)
from rest_framework.exceptions import NotFound
from apps.universities.api.public.serializers.public_serializers import (
    PublicUniversityListSerializer,
    PublicUniversityDetailSerializer,
)



class PublicUniversityListAPIView(APIView):
    pagination_class = StandardResultsPagination

    authentication_classes = []
    permission_classes = []

    @extend_schema(
        tags=["Public - Universities"],
        responses={200: PublicUniversityListSerializer(many=True)},
    )
    def get(self, request):
        language_code = request.query_params.get("lang", "uz")

        queryset = UniversitySelector.get_public_university_queryset(
            language_code=language_code,
        )

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)

        serializer = PublicUniversityListSerializer(
            page,
            many=True,
            context={"language_code": language_code,},
        )

        return paginator.get_paginated_response(serializer.data)



class PublicUniversityDetailAPIView(APIView):
    authentication_classes = []
    permission_classes = []

    @extend_schema(
        tags=["Public - Universities"],
        responses={200: PublicUniversityDetailSerializer},
    )
    def get(self, request, slug):
        language_code = request.query_params.get("lang", "uz")

        university, resolved_language = (
            UniversitySelector.get_public_university_by_slug(
                slug=slug,
                language_code=language_code,
            )
        )

        if university is None:
            raise NotFound("Universitet topilmadi.")

        serializer = PublicUniversityDetailSerializer(
            university,
            context={
                "language_code": resolved_language,
            },
        )

        return Response(serializer.data)

