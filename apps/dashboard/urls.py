from django.urls import path
from django.conf import settings

from dashboard.views import (
    UserListView,
    TournamentListCreateView,
    TournamentRetrieveUpdateDeleteView,
    SportListCreateView,
    SportRetrieveUpdateDeleteView,
    TeamListCreateView,
    TeamRetrieveUpdateDeleteView,
    SchoolListCreateView,
    SchoolRetrieveUpdateDeleteView,
    ExportView,
    TermsOfConditionAddListView,
    TermsOfConditionDetailUpdateDeleteView,
    PrivacyPolicyAddListView,
    PrivacyPolicyDetailUpdateDeleteView,
)

app_name = "dashboard"

urlpatterns = [
    path("users/", UserListView.as_view(), name='users-list'),

    path("tournament/", TournamentListCreateView.as_view(), name='tournament-create-list'),
    path("tournament/<uuid:pk>/", TournamentRetrieveUpdateDeleteView.as_view(), name='tournament-retrieve-update-delete'),

    path("sport/", SportListCreateView.as_view(), name='sport-create-list'),
    path("sport/<uuid:pk>/", SportRetrieveUpdateDeleteView.as_view(), name='sport-retrieve-update-delete'),

    path("team/", TeamListCreateView.as_view(), name='team-create-list'),
    path("team/<uuid:pk>/", TeamRetrieveUpdateDeleteView.as_view(), name='team-retrieve-update-delete'),

    path("export-excel/", ExportView.as_view(), name='export-excel'),

    path("school/", SchoolListCreateView.as_view(), name='school-create-list'),
    path("school/<uuid:pk>/", SchoolRetrieveUpdateDeleteView.as_view(), name='school-retrieve-update-delete'),

    path("privacy-policy/", PrivacyPolicyAddListView.as_view(), name="privacy-policy-create-list"),
    path("privacy-policy/<uuid:pk>/", PrivacyPolicyDetailUpdateDeleteView.as_view(), name="privacy-policy-detail-update-delete"),

    path("terms-of-condition/", TermsOfConditionAddListView.as_view(), name="terms-of-condition-create"),
    path("terms-of-condition/<uuid:pk>/", TermsOfConditionDetailUpdateDeleteView.as_view(), name="terms-of-condition-detail-update-delete"),
]
