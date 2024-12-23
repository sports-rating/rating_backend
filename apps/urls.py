from django.urls import path, include

urlpatterns = [
    path("user/", include(("user.urls", "user"), "user")),
    path("dashboard/", include(("dashboard.urls", "dashboard"), "dashboard")),
]