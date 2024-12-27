from django.utils.translation import gettext as _, get_language
from django_filters.rest_framework import DjangoFilterBackend
from django.utils.dateparse import parse_date
from django.utils.timezone import make_aware

from rest_framework.views import APIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import generics, permissions, status, filters as rest_framework_filters

from datetime import datetime

from shared.addons.pagination import CustomPagination
from shared.addons.utils import (
    success_response,
    error_response
)

from user.models import (
    User,
    Sportsman,
    Trainer,
)

from dashboard.models import (
    Tournament
)

from user.serializers import (
    UsersMeSerializer
)

from dashboard.serializers import (
    UserListSerializer,
    TournamentCreateSerializer,
    TournamentSerializer
)

from .filters import (
    UserFilter,
    TournamentFilter
)

from shared.addons.exceptions import raise_validation_error

class UserListView(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserListSerializer
    permission_classes = (
        permissions.AllowAny,
    )
    filter_backends = [DjangoFilterBackend]
    filterset_class = UserFilter
    pagination_class = CustomPagination

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return success_response(
            data=serializer.data, 
            message=_("Users list"),
            code=200,
        )


class TournamentListCreateView(generics.ListCreateAPIView):
    permission_classes = (permissions.AllowAny,)
    queryset = Tournament.objects.all()
    serializer_class = TournamentCreateSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = TournamentFilter
    pagination_class = CustomPagination

    def get_serializer_class(self):
        if self.request.method == "GET":
            return TournamentSerializer
        return super().get_serializer_class()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(
            data=serializer.data,
            message=_("Tournament created successfully"),
            code=200
        )
    
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return success_response(
            data=serializer.data,
            message=_("Tournament list retrieved successfully"),
            code=200
        )


class TournamentRetrieveUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = (permissions.AllowAny,)
    queryset = Tournament.objects.all()
    serializer_class = TournamentCreateSerializer

    def get_serializer_class(self):
        if self.request.method == "GET":
            return TournamentSerializer
        return super().get_serializer_class()

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return success_response(
            data=serializer.data,
            message=_("Tournament retrieved successfully"),
            code=200,
        )
    
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(
            message=_("Tournament is updated successfully"),
            data=serializer.data,
            code=200,
        )

    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return success_response(
            message=_("Tournament is deleted successfully"),
            code=204
        )