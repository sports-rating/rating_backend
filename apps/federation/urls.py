from django.urls import path

import apps.federation.views as views

app_name = "federation"

urlpatterns = [
    path("", views.FederationListCreateAPIView.as_view(), name='federation-create-list'),
    path("<uuid:pk>/", views.FederationRetrieveUpdateDeleteAPIView.as_view(), name='federation-retrieve-update-delete'),
    path("<uuid:pk>/users/", views.FederationUserListAPIView.as_view(), name='user-list'),
    path("<uuid:pk>/regional-federations/", views.RegionalFederationListCreateAPIView.as_view(), name='regional-federation-list-create'),

    path("<uuid:pk>/requests/", views.FederationUserRequestListAPIView.as_view(), name='federation-request-list'),
    path("<uuid:pk>/tournaments/", views.FederationTournamentListAPIView.as_view(), name='federation-tournament-list'),
    path("<uuid:pk>/age-groups/", views.FederationAgeGroupListCreateAPIView.as_view(), name='federation-age-group-list-create'),

    path("age-groups/<uuid:pk>/", views.AgeGroupRetrieveUpdateDeleteAPIView.as_view(), name='age-group-retrieve-update-delete'),
]
