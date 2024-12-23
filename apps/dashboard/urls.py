from django.urls import path
from django.conf import settings

from dashboard.views import (
    UserListView,
)

app_name = "dashboard"

urlpatterns = [
    path("users/", UserListView.as_view(), name='users-list'),
]
