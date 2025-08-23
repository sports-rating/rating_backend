from django.urls import path, include

urlpatterns = [
    path("user/", include(("user.urls", "user"), "user")),
    path("sport/", include(("sport.urls", "sport"), "sport")),
    path("education/", include(("education.urls", "education"), "education")),
    path("dashboard/", include(("dashboard.urls", "dashboard"), "dashboard")),
    path("federation/", include(("federation.urls", "federation"), "federation")),
    path("payment/", include(("payment.urls", "payment"), "payment")),
]
