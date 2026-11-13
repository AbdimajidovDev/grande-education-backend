
from rest_framework import generics, serializers
from rest_framework.permissions import AllowAny

from drf_spectacular.utils import (
    extend_schema,
    OpenApiParameter,
    OpenApiResponse,
)

from apps.teachers.models import TeacherTranslation
from apps.teachers.selectors import get_public_teachers
from apps.teachers.api.serializers import TeacherPublicSerializer


class PublicTeacherListView(generics.ListAPIView):
    serializer_class = TeacherPublicSerializer
    permission_classes = [AllowAny]
    pagination_class = None

    def get_language_code(self):
        language_code = self.request.query_params.get("lang", "uz")

        if language_code not in TeacherTranslation.Language.values:
            raise serializers.ValidationError({
                "lang": "Qo'llab-quvvatlanmaydigan til kodi."
            })

        return language_code

    @extend_schema(
        tags=["Public - Teachers"],
        summary="Public teachers list",
        description=(
            "Faol o'qituvchilar ro'yxatini so'ralgan tilda qaytaradi. "
            "Tarjima topilmasa, o'zbekcha tarjimadan foydalanadi."
        ),
        parameters=[
            OpenApiParameter(
                name="lang",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Til kodi: uz, ru, en, zh, ja, de",
                enum=TeacherTranslation.Language.values,
            ),
        ],
        responses={
            200: TeacherPublicSerializer(many=True),
            400: OpenApiResponse(description="Noto'g'ri til kodi"),
        },
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        return get_public_teachers(
            language_code=self.get_language_code()
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["language_code"] = self.get_language_code()
        return context
