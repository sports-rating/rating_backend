from django.urls import path
from django.conf import settings

from user.views import (
    SendVerificationCodeView,
    VerifyCodeView,
    RegistrationView,
    LoginRefreshView,
    LogoutView,
    UserRetrieveUpdateView,
    ChangePasswordView,
    UserPhoneUpdateView,
    UserPhoneUpdateConfirmView,
)

app_name = "user"

urlpatterns = [
    path("auth/send-code/", SendVerificationCodeView.as_view(), name='send-code'),
    path("auth/verify-code/", VerifyCodeView.as_view(), name='verify-code'),
    path("auth/register/", RegistrationView.as_view(), name='registration'),
    path("profile/", UserRetrieveUpdateView.as_view(), name='profile-retrieve-update'),
    path("logout/", LogoutView.as_view()),
    path("refresh-token/", LoginRefreshView.as_view()),
]

if settings.DEBUG:
    from rest_framework_simplejwt.views import TokenObtainPairView

    urlpatterns.append(
        path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    )