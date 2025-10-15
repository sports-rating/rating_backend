from django.urls import path

import apps.dashboard.views as views

app_name = "dashboard"

urlpatterns = [
    path("users/", views.UserListView.as_view(), name='users-list'),
    path("add-user/", views.AddUserAPIView.as_view(), name='add-user'),

    path("export-excel/", views.ExportView.as_view(), name='export-excel'),

    path("privacy-policy/", views.PrivacyPolicyAddListView.as_view(), name="privacy-policy-create-list"),
    path("privacy-policy/<uuid:pk>/", views.PrivacyPolicyDetailUpdateDeleteView.as_view(), name="privacy-policy-detail-update-delete"),

    path("terms-of-condition/", views.TermsOfConditionAddListView.as_view(), name="terms-of-condition-create"),
    path("terms-of-condition/<uuid:pk>/", views.TermsOfConditionDetailUpdateDeleteView.as_view(), name="terms-of-condition-detail-update-delete"),

    path("stats/main/", views.MainStatsAPIView.as_view(), name="main-stats"),
    path("stats/payments/", views.PaymentStatsAPIView.as_view(), name="payment-stats"),
    path("stats/requests/", views.RequestStatsAPIView.as_view(), name="request-stats"),

    path("requests/", views.UserRequestListAPIView.as_view(), name="user-requests-list"),
    path("requests/<uuid:pk>/", views.UserRequestDetailAPIView.as_view(), name="user-requests-detail"),
]
