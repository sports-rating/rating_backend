from django.urls import path
from django.conf import settings

from dashboard.views import (
    UserListView,
    TournamentListCreateView,
    TournamentRetrieveUpdateDeleteView
)

app_name = "dashboard"

urlpatterns = [
    path("users/", UserListView.as_view(), name='users-list'),

    path("tournament/", TournamentListCreateView.as_view(), name='tournament-create-list'),
    path("tournament/<uuid:pk>/", TournamentRetrieveUpdateDeleteView.as_view(), name='tournament-retrieve-update-delete'),
]
