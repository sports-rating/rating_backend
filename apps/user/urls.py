from django.urls import path
from django.conf import settings

import apps.user.views as views

app_name = "user"

urlpatterns = [
    path("auth/send-code/", views.SendVerificationCodeView.as_view(), name='send-code'),
    path("auth/verify-code/", views.VerifyCodeView.as_view(), name='verify-code'),
    path("auth/register/", views.RegistrationView.as_view(), name='registration'),
    path("auth/logout/", views.LogoutView.as_view(), name='logout'),
    path("auth/refresh-token/", views.LoginRefreshView.as_view(), name='refresh-token'),
    path("auth/delete-account/", views.DeleteAccountAPIView.as_view(), name='delete-account'),

    path("profile/", views.UserRetrieveUpdateView.as_view(), name='profile-retrieve-update'),
    path("profile/results/", views.SportsmanResultListCreateAPIView.as_view(), name='result-list-create'),
    path("profile/results/<uuid:pk>/", views.SportsmanResultRetrieveUpdateDeleteAPIView.as_view(), name='result-retrieve-update-delete'),
    path("profile/media/", views.UserMediaListView.as_view(), name='user-media-list'),

    path("profile/sportsman/", views.SportsmanListCreateView.as_view(), name='sportsman-register-public-list'),
    path("profile/sportsman/<uuid:pk>/", views.SportsmanRetrieveUpdateDeleteView.as_view(), name='sportsman-public-retrieve-update-delete'),

    path("profile/trainer/", views.TrainerListCreateView.as_view(), name='trainer-register-public-list'),
    path("profile/trainer/<uuid:pk>/", views.TrainerRetrieveUpdateDeleteView.as_view(), name="trainer-retrieve"),

    path("profile/archived-trainer/", views.ArchivedTrainerCreateListView.as_view(), name='archived-trainer-register-list'),
    path("profile/archived-trainer/<uuid:pk>/", views.ArchivedTrainerRetrieveUpdateDeleteView.as_view(), name='archived-trainer-retrieve-update-delete'),

    path("sportsmen/", views.SportsmanListAPIView.as_view(), name='internal-sportsman-list'),
    path("trainers/", views.TrainerListAPIView.as_view(), name='internal-trainer-list'),

    path("media-upload/", views.MediaUploadView.as_view(), name='media-upload'),
    path("media/<uuid:pk>/", views.MediaDeleteView.as_view(), name='media-delete'),

    path("notifications/", views.UserNotificationsListView.as_view()),
    path("notifications/<str:notification_id>/mark-as-read/", views.UserNotificationMarkAsReadView.as_view()),

    path("requests/", views.UserRequestListCreateView.as_view(), name='user-request-list-create'),
    path("requests/<uuid:pk>/", views.UserRequestRetrieveUpdateDeleteView.as_view(), name='user-request-retrieve-update-delete'),

    path("regions/", views.RegionListView.as_view(), name='region-list'),
    path("districts/", views.DistrictListView.as_view(), name='district-list'),
    path("neighborhoods/", views.NeighborhoodListView.as_view(), name='neighborhood-list'),

    path("recalculate-points/", views.RecalculatePointsAPIView.as_view(), name='recalculate-points'),
]

if settings.DEBUG:
    from rest_framework_simplejwt.views import TokenObtainPairView

    urlpatterns.append(
        path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    )
