from django.middleware.csrf import get_token

from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.utils import extend_schema


class CSRFTokenAPIView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Authentication"],
        summary="Get CSRF token",
        description="Returns a CSRF token and sets the CSRF cookie.",
        responses={200: None},
    )
    def get(self, request):
        csrf_token = get_token(request)

        return Response({
            "csrfToken": csrf_token,
        })