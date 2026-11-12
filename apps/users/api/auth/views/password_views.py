
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from apps.users.api.auth.serializers import (
    ChangePasswordSerializer,
    ForgotPasswordSerializer,
)
from apps.users.services.password_service import PasswordService
from apps.users.services.forgot_password_service import ForgotPasswordService

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode

from apps.users.services.password_reset_service import PasswordResetService
from apps.users.api.auth.serializers import ResetPasswordSerializer
from apps.common.throttling import (
    PasswordResetRequestIPThrottle,
    PasswordResetRequestEmailThrottle,
)
from apps.common.throttling import PasswordResetConfirmIPThrottle


class ChangePasswordAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Authentication"],
        summary="Change password",
        description="Authenticated user can change their password.",
        request=ChangePasswordSerializer,
        responses={200: None},
    )
    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        PasswordService.change_password(
            user=request.user,
            new_password=serializer.validated_data["new_password"],
        )

        return Response(
            {"detail": "Password changed successfully."},
            status=status.HTTP_200_OK,
        )


class ForgotPasswordAPIView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    throttle_classes = [
        PasswordResetRequestIPThrottle,
        PasswordResetRequestEmailThrottle,
    ]

    @extend_schema(
        tags=["Authentication"],
        summary="Forgot password",
        description="Sends a password reset email if the account exists.",
        request=ForgotPasswordSerializer,
        responses={200: None},
    )
    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ForgotPasswordService.request_password_reset(
            email=serializer.validated_data["email"],
        )

        return Response(
            {
                "detail": (
                    "If an account with this email exists, "
                    "password reset instructions will be sent."
                )
            },
            status=status.HTTP_200_OK,
        )



class ResetPasswordAPIView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [PasswordResetConfirmIPThrottle]

    @extend_schema(
        tags=["Authentication"],
        summary="Reset password",
        description="Resets user password using a valid reset token.",
        request=ResetPasswordSerializer,
        responses={200: None},
    )
    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user_id = force_str(
                urlsafe_base64_decode(
                    serializer.validated_data["uid"]
                )
            )

            user_id = int(user_id)

        except (ValueError, TypeError, OverflowError):
            return Response(
                {"detail": "Invalid or expired password reset link."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from apps.users.models import User

        user = User.objects.filter(
            pk=user_id,
            is_active=True,
        ).first()

        if user is None:
            return Response(
                {"detail": "Invalid or expired password reset link."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        new_password = serializer.validated_data["new_password"]

        try:
            validate_password(new_password, user=user)
        except DjangoValidationError as exc:
            return Response(
                {"new_password": list(exc.messages)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        success = PasswordResetService.reset_password(
            user_id=user_id,
            raw_token=serializer.validated_data["token"],
            new_password=new_password,
        )

        if not success:
            return Response(
                {"detail": "Invalid or expired password reset link."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {"detail": "Password has been reset successfully."},
            status=status.HTTP_200_OK,
        )

