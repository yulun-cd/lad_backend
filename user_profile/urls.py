from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from user_profile.auth_views import (
    EmailOrUsernameLoginView,
    MeView,
    RegisterView,
    ChangePasswordView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="auth-register"),
    path("login/", EmailOrUsernameLoginView.as_view(), name="auth-login"),
    path("refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("me/", MeView.as_view(), name="auth-me"),
    path("change-password/", ChangePasswordView.as_view(), name="change-password"),
]
