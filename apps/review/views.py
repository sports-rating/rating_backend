import typing as t
from uuid import UUID

from django.utils.translation import gettext as _, get_language
from django_filters.rest_framework import DjangoFilterBackend
from django.utils.dateparse import parse_date
from django.utils.timezone import make_aware
from django.http import HttpResponse
from django.db.models import Q, Prefetch, QuerySet

from rest_framework.views import APIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework import generics, permissions, status, filters as rest_framework_filters
from rest_framework.parsers import MultiPartParser, FormParser

from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

from apps.shared.utils.permissions import IsAdmin, IsAdminOrSuperAdmin
from apps.shared.utils.pagination import CustomPagination
from apps.shared.utils.utils import (
    success_response,
    error_response
)
from apps.shared.utils import enums
from apps.shared.utils.exceptions import raise_validation_error

from apps.review.models import Comment
from apps.review.serializers import (
    CommentSerializer
)
from apps.review.filters import CommentFilter


class CommentListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = CommentSerializer
    permission_classes = [permissions.AllowAny,]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = CommentFilter
    search_fields = ['user__first_name', 'user__last_name', 'text']
    ordering_fields = ['created_time', 'rating']
    pagination_class = CustomPagination

    def get_queryset(self) -> QuerySet:
        sport_institution_id = self.request.query_params.get('sport_institution_id')
        if sport_institution_id:
            return Comment.objects.select_related('user', 'sport_institution').filter(
                sport_institution__id=sport_institution_id
            ).order_by('-created_time')
        return Comment.objects.select_related(
            'user', 'sport_institution'
            ).all().order_by('-created_time')

    def get_permissions(self):
        if self.request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            return [permissions.IsAuthenticated()]
        return super().get_permissions()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({"request": self.request})
        return context

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(
            data=serializer.data,
            message=_("Comment created successfully."),
            code=status.HTTP_201_CREATED
        )

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        return success_response(
            data=response.data,
            message=_("Comments retrieved successfully."),
            code=status.HTTP_200_OK
        )


class CommentRetrieveUpdateDeleteAPIView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CommentSerializer
    permission_classes = [permissions.AllowAny,]
    queryset = Comment.objects.all()

    def get_queryset(self) -> QuerySet:
        return Comment.objects.select_related('user', 'sport_institution').all()

    def get_permissions(self):
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            return [permissions.IsAuthenticated()]
        return super().get_permissions()

    def get_serializer_context(self) -> dict:
        context: dict = super().get_serializer_context()
        context.update({"request": self.request})
        return context

    def get_object(self):
        comment_id = self.kwargs.get("pk")
        comment = self.get_queryset().filter(id=comment_id).first()
        if not comment:
            raise_validation_error(message=_("Comment not found."))
        return comment

    def retrieve(self, request: Request, *args, **kwargs) -> Response:
        instance: Comment = self.get_object()
        serializer = self.get_serializer(instance)
        return success_response(
            data=serializer.data,
            message=_("Comment retrieved successfully."),
            code=status.HTTP_200_OK
        )

    def update(self, request: Request, *args, **kwargs) -> Response:
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(
            data=serializer.data,
            message=_("Comment updated successfully."),
            code=status.HTTP_200_OK
        )

    def destroy(self, request: Request, *args, **kwargs) -> Response:
        instance = self.get_object()
        instance.delete()
        return success_response(
            data=None,
            message=_("Comment deleted successfully."),
            code=status.HTTP_204_NO_CONTENT
        )
