from django.urls import path

import apps.federation.views as views

app_name = "federation"

urlpatterns = [
    path("", views.FederationListCreateAPIView.as_view(), name='federation-create-list'),
    path("<uuid:pk>/", views.FederationRetrieveUpdateDeleteAPIView.as_view(), name='federation-retrieve-update-delete'),
    path("users/", views.UserListAPIView.as_view(), name='user-list'),
]
