from django.urls import path
from django.conf import settings


from education.views import (
    EducationRetrieveUpdateDestroyView,
    SchoolListCreateView,
    SchoolRetrieveUpdateDeleteView
)

app_name = "education"

urlpatterns = [
    path("school/", SchoolListCreateView.as_view(), name='school-create-list'),
    path("school/<uuid:pk>/", SchoolRetrieveUpdateDeleteView.as_view(), name='school-retrieve-update-delete'),
]
