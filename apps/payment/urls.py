from django.urls import path

import apps.payment.views as views

app_name = "payment"

urlpatterns = [
    path("payme/webhook/", views.PaymeWebhookAPIView.as_view(), name="payme-webhook"),
    path("create-checkout/", views.CreateCheckoutAPIView.as_view(), name="create-checkout"),
]
