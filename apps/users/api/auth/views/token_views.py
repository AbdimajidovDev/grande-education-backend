from django.conf import settings
from django.contrib.auth import get_user_model

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from drf_spectacular.utils import extend_schema
from apps.users.api.auth.authentication import CookieJWTAuthentication


User = get_user_model()


class RefreshTokenAPIView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Authentication"],
        summary="Refresh JWT tokens",
        responses={200: None},
    )
    def post(self, request):
        CookieJWTAuthentication.enforce_csrf(request)

        raw_refresh = request.COOKIES.get(settings.AUTH_COOKIE_REFRESH)

        if not raw_refresh:
            raise InvalidToken("Refresh token is missing.")

        try:
            old_refresh = RefreshToken(raw_refresh)
            user_id = old_refresh.payload.get("user_id")

            user = User.objects.get(pk=user_id, is_active=True)

            old_refresh.blacklist()

            new_refresh = RefreshToken.for_user(user)
            access_token = str(new_refresh.access_token)
            refresh_token = str(new_refresh)

        except (TokenError, User.DoesNotExist, TypeError, ValueError):
            raise InvalidToken("Invalid refresh token.")

        response = Response(
            {"detail": "Token refreshed successfully."},
            status=status.HTTP_200_OK,
        )

        cookie_settings = {
            "httponly": settings.AUTH_COOKIE_HTTPONLY,
            "secure": settings.AUTH_COOKIE_SECURE,
            "samesite": settings.AUTH_COOKIE_SAMESITE,
            "path": settings.AUTH_COOKIE_PATH,
        }

        response.set_cookie(
            settings.AUTH_COOKIE_ACCESS,
            access_token,
            max_age=int(settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds()),
            **cookie_settings,
        )

        response.set_cookie(
            settings.AUTH_COOKIE_REFRESH,
            refresh_token,
            max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
            **cookie_settings,
        )

        return response