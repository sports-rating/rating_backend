from django.urls import path
from django.conf import settings

from dashboard.views import (
    UserListView,
    ExportView,
    TermsOfConditionAddListView,
    TermsOfConditionDetailUpdateDeleteView,
    PrivacyPolicyAddListView,
    PrivacyPolicyDetailUpdateDeleteView,
)

app_name = "dashboard"

urlpatterns = [
    path("users/", UserListView.as_view(), name='users-list'),

    path("export-excel/", ExportView.as_view(), name='export-excel'),
    
    path("privacy-policy/", PrivacyPolicyAddListView.as_view(), name="privacy-policy-create-list"),
    path("privacy-policy/<uuid:pk>/", PrivacyPolicyDetailUpdateDeleteView.as_view(), name="privacy-policy-detail-update-delete"),

    path("terms-of-condition/", TermsOfConditionAddListView.as_view(), name="terms-of-condition-create"),
    path("terms-of-condition/<uuid:pk>/", TermsOfConditionDetailUpdateDeleteView.as_view(), name="terms-of-condition-detail-update-delete"),
]
