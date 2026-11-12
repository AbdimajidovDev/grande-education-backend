from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.utils import extend_schema

from apps.users.api.auth.serializers import MeSerializer


class MeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Authentication"],
        summary="Get current user",
        description="Returns the authenticated user's profile and roles.",
        responses={200: MeSerializer},
    )
    def get(self, request):
        user = (
            request.user.__class__.objects
            .prefetch_related("groups")
            .get(pk=request.user.pk)
        )

        serializer = MeSerializer(user)
        return Response(serializer.data)

