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
    SportsmanListCreateView,
    SportsmanRetrieveUpdateDeleteView,
    TrainerListCreateView,
    TrainerRetrieveView,
    MediaUploadView,
    MediaDeleteView,
    ResultRetrieveUpdateDestroyView,
    EducationRetrieveUpdateDestroyView,
)

app_name = "user"

urlpatterns = [
    path("auth/send-code/", SendVerificationCodeView.as_view(), name='send-code'),
    path("auth/verify-code/", VerifyCodeView.as_view(), name='verify-code'),
    path("auth/register/", RegistrationView.as_view(), name='registration'),
    path("profile/", UserRetrieveUpdateView.as_view(), name='profile-retrieve-update'),
    path("logout/", LogoutView.as_view()),
    path("refresh-token/", LoginRefreshView.as_view()),
    path("profile/sportsman/", SportsmanListCreateView.as_view(), name='sportsman-register-list'),
    path("profile/sportsman/<uuid:pk>/", SportsmanRetrieveUpdateDeleteView.as_view(), name='sportsman-retrieve-update-delete'),
    path("profile/trainer/", TrainerListCreateView.as_view(), name='trainer-register-list'),
    path("profile/trainer/<uuid:pk>/", TrainerRetrieveView.as_view(), name="trainer-retrieve"),
    path("media-upload/", MediaUploadView.as_view(), name='media-upload'),
    path("media/<uuid:pk>/", MediaDeleteView.as_view(), name='media-delete'),
    # path("profile/sportsman/results/<uuid:pk>/", ResultRetrieveUpdateDestroyView.as_view(), name='result-retrieve-update-delete'),
    # path("profile/sportsman/educations/<uuid:pk>/", EducationRetrieveUpdateDestroyView.as_view(), name='education-retrieve-update-delete'),
]

if settings.DEBUG:
    from rest_framework_simplejwt.views import TokenObtainPairView

    urlpatterns.append(
        path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    )