from django.urls import path
from django.conf import settings

import apps.career.views as views

app_name = "career"

urlpatterns = [
    path("work-place/", views.TrainerWorkPlaceListCreateView.as_view(), name="trainer-work_place-list-create"),

    path("education/", views.EducationListCreateAPIView.as_view(), name="education-list-create"),
    path("education/<uuid:pk>/", views.EducationRetrieveUpdateDeleteAPIView.as_view(), name="education-retrieve-update-delete"),
]
