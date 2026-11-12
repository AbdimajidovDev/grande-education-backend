from django.conf import settings

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from drf_spectacular.utils import extend_schema

from apps.users.api.auth.authentication import CookieJWTAuthentication


class LogoutAPIView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Authentication"],
        summary="User logout",
        description="Blacklists the refresh token and clears authentication cookies.",
        responses={200: None},
    )
    def post(self, request):
        CookieJWTAuthentication.enforce_csrf(request)

        raw_refresh = request.COOKIES.get(
            settings.AUTH_COOKIE_REFRESH
        )

        if raw_refresh:
            try:
                refresh = RefreshToken(raw_refresh)
                refresh.blacklist()
            except TokenError:
                pass

        response = Response(
            {"detail": "Logout successful."},
            status=status.HTTP_200_OK,
        )

        cookie_settings = {
            "path": settings.AUTH_COOKIE_PATH,
            "samesite": settings.AUTH_COOKIE_SAMESITE,
        }

        response.delete_cookie(
            settings.AUTH_COOKIE_ACCESS,
            **cookie_settings,
        )

        response.delete_cookie(
            settings.AUTH_COOKIE_REFRESH,
            **cookie_settings,
        )

        return response
