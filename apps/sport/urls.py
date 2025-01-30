from django.urls import path

from sport.views import (
    ResultRetrieveUpdateDestroyView,
    TournamentListCreateView,
    TournamentRetrieveUpdateDeleteView,
    SportListCreateView,
    SportRetrieveUpdateDeleteView,
    TeamListCreateView,
    TeamRetrieveUpdateDeleteView,
)

app_name = "sport"

urlpatterns = [
    path("tournament/", TournamentListCreateView.as_view(), name='tournament-create-list'),
    path("tournament/<uuid:pk>/", TournamentRetrieveUpdateDeleteView.as_view(), name='tournament-retrieve-update-delete'),

    path("team/", TeamListCreateView.as_view(), name='team-create-list'),
    path("team/<uuid:pk>/", TeamRetrieveUpdateDeleteView.as_view(), name='team-retrieve-update-delete'),

    path("", SportListCreateView.as_view(), name='sport-create-list'),
    path("<uuid:pk>/", SportRetrieveUpdateDeleteView.as_view(), name='sport-retrieve-update-delete'),

]