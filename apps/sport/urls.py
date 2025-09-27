from django.urls import path

import apps.sport.views as views

app_name = "sport"

urlpatterns = [
    path("tournament/", views.TournamentListCreateView.as_view(), name='tournament-create-list'),
    path("tournament/<uuid:pk>/", views.TournamentRetrieveUpdateDeleteView.as_view(), name='tournament-retrieve-update-delete'),

    path("team/", views.TeamListCreateView.as_view(), name='team-create-list'),
    path("team/<uuid:pk>/", views.TeamRetrieveUpdateDeleteView.as_view(), name='team-retrieve-update-delete'),

    path("school/", views.SchoolListCreateView.as_view(), name='school-create-list'),
    path("school/<uuid:pk>/", views.SchoolRetrieveUpdateDeleteView.as_view(), name='school-retrieve-update-delete'),

    path("", views.SportListCreateView.as_view(), name='sport-create-list'),
    path("<uuid:pk>/", views.SportRetrieveUpdateDeleteView.as_view(), name='sport-retrieve-update-delete'),
]
