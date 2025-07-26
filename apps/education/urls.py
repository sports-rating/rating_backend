from django.urls import path
from django.conf import settings

import apps.education.views as views

app_name = "education"

urlpatterns = [
    path("school/", views.SchoolListCreateView.as_view(), name='school-create-list'),
    path("school/<uuid:pk>/", views.SchoolRetrieveUpdateDeleteView.as_view(), name='school-retrieve-update-delete'),
]
