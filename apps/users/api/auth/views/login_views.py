from django.conf import settings
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from drf_spectacular.utils import extend_schema

from apps.users.api.auth.serializers import LoginSerializer


class LoginAPIView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Authentication"],
        summary="User login",
        description=(
            "Authenticates a user using username and password. "
            "Returns user information and sets JWT tokens in HttpOnly cookies."
        ),
        request=LoginSerializer,
        responses={200: None},
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        access_token = serializer.validated_data["access"]
        refresh_token = serializer.validated_data["refresh"]

        response = Response(
            {
                "detail": "Login successful.",
                "user": {
                    "id": serializer.user.id,
                    "username": serializer.user.username,
                },
            },
            status=status.HTTP_200_OK,
        )

        cookie_settings = {
            "httponly": settings.AUTH_COOKIE_HTTPONLY,
            "secure": settings.AUTH_COOKIE_SECURE,
            "samesite": settings.AUTH_COOKIE_SAMESITE,
            "path": settings.AUTH_COOKIE_PATH,
        }

        response.set_cookie(
            key=settings.AUTH_COOKIE_ACCESS,
            value=access_token,
            max_age=int(settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds()),
            **cookie_settings,
        )

        response.set_cookie(
            key=settings.AUTH_COOKIE_REFRESH,
            value=refresh_token,
            max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
            **cookie_settings,
        )

        return response
