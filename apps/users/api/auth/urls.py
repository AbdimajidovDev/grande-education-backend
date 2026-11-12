from django.urls import path

from apps.users.api.auth.views.csrf_views import CSRFTokenAPIView
from apps.users.api.auth.views.login_views import LoginAPIView
from apps.users.api.auth.views.token_views import RefreshTokenAPIView
from apps.users.api.auth.views.logout_views import LogoutAPIView
from apps.users.api.auth.views.profile_views import MeAPIView
from apps.users.api.auth.views.password_views import ChangePasswordAPIView
from apps.users.api.auth.views.password_views import ForgotPasswordAPIView
from apps.users.api.auth.views.password_views import ResetPasswordAPIView


urlpatterns = [
    path("csrf/", CSRFTokenAPIView.as_view(), name="csrf-token"),
    path("login/", LoginAPIView.as_view(), name="login"),
    path("refresh/", RefreshTokenAPIView.as_view(), name="token-refresh"),
    path("logout/", LogoutAPIView.as_view(), name="logout"),

    path("change-password/", ChangePasswordAPIView.as_view(), name="change-password",),
    path("forgot-password/", ForgotPasswordAPIView.as_view(), name="forgot-password",),
    path("reset-password/", ResetPasswordAPIView.as_view(), name="reset-password", ),

    path("me/", MeAPIView.as_view(), name="me"),

]