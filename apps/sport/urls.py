from django.urls import path

import apps.sport.views as views

app_name = "sport"

urlpatterns = [
    path("tournament/", views.TournamentListCreateView.as_view(), name='tournament-create-list'),
    path("tournament/<uuid:pk>/", views.TournamentRetrieveUpdateDeleteView.as_view(), name='tournament-retrieve-update-delete'),

    path("team/", views.TeamListCreateView.as_view(), name='team-create-list'),
    path("team/<uuid:pk>/", views.TeamRetrieveUpdateDeleteView.as_view(), name='team-retrieve-update-delete'),

    path("", views.SportListCreateView.as_view(), name='sport-create-list'),
    path("<uuid:pk>/", views.SportRetrieveUpdateDeleteView.as_view(), name='sport-retrieve-update-delete'),

    path("federations/", views.FederationListCreateAPIView.as_view(), name='federation-create-list'),
    path("federation/<uuid:pk>/", views.FederationRetrieveUpdateDeleteAPIView.as_view(), name='federation-retrieve-update-delete')
]
