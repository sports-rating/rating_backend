from django.urls import path
from django.conf import settings

import apps.career.views as views

app_name = "career"

urlpatterns = [
    path("work-place/", views.TrainerWorkPlaceListCreateView.as_view(), name="trainer-work_place-list-create"),
]
