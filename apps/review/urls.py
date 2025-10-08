from django.urls import path, include
from django.conf import settings

import apps.review.views as views


urlpatterns = [
    path("comment/", views.CommentListCreateAPIView.as_view(), name='comment-list-create'),
    path("comment/<uuid:pk>/", views.CommentRetrieveUpdateDeleteAPIView.as_view(), name='comment-retrieve-update-delete'),
]
