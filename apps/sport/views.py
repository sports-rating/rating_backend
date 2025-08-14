from django.utils.translation import gettext as _, get_language
from django_filters.rest_framework import DjangoFilterBackend
from django.utils.dateparse import parse_date
from django.utils.timezone import make_aware
from django.http import HttpResponse
from django.db.models import Q, Prefetch

from rest_framework.views import APIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework import generics, permissions, status, filters as rest_framework_filters
from rest_framework.parsers import MultiPartParser, FormParser

from apps.shared.utils.permissions import IsAdmin, IsAdminOrSuperAdmin
from apps.shared.utils.pagination import CustomPagination
from apps.shared.utils.utils import (
    success_response,
    error_response
)

from apps.sport.models import (
    Sport,
    Result,
    Tournament,
    Team,
)

import apps.sport.serializers as serializer

from apps.sport.filters import (
    TournamentFilter,
    TeamFilter
)


class ResultRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = (permissions.AllowAny, )
    queryset = Result.objects.all().select_related('trainer', 'archived_trainer', 'tournament')
    serializer_class = serializer.ResultCreateSerializer

    def get_serializer_class(self):
        if self.request.method == "GET":
            return serializer.ResultSerializer
        return super().get_serializer_class()

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return success_response(
            data=serializer.data,
            message=_("Result retrieved successfully"),
            code=200,
        )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(
            data=serializer.data,
            message=_("Result updated successfully"),
            code=200,
        )

    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return success_response(
            message=_("Result deleted successfully"),
            code=204
        )


class TournamentListCreateView(generics.ListCreateAPIView):
    permission_classes = (IsAdminOrSuperAdmin,)
    queryset = Tournament.objects.all()
    serializer_class = serializer.TournamentSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = TournamentFilter
    search_fields = ["name",]
    pagination_class = CustomPagination

    def get_queryset(self):
        name = self.request.query_params.get("name")
        if name:
            return self.queryset.select_related("sport").filter(name__icontains=name)
        return self.queryset.select_related("sport")

    def get_permissions(self):
        if self.request.method == "GET":
            return (permissions.AllowAny(),)
        return super().get_permissions()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(
            data=serializer.data,
            message=_("Tournament created successfully"),
            code=status.HTTP_201_CREATED
        )

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return success_response(
            data=serializer.data,
            message=_("Tournament list retrieved successfully"),
            code=status.HTTP_200_OK
        )


class TournamentRetrieveUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = (IsAdminOrSuperAdmin,)
    queryset = Tournament.objects.all()
    serializer_class = serializer.TournamentSerializer

    def get_queryset(self):
        return self.queryset.select_related("sport")

    def get_permissions(self):
        if self.request.method == "GET":
            return (permissions.AllowAny(),)
        return super().get_permissions()

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return success_response(
            data=serializer.data,
            message=_("Tournament retrieved successfully"),
            code=status.HTTP_200_OK,
        )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(
            message=_("Tournament is updated successfully"),
            data=serializer.data,
            code=status.HTTP_200_OK,
        )

    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return success_response(
            message=_("Tournament is deleted successfully"),
            code=status.HTTP_204_NO_CONTENT
        )


class SportListCreateView(generics.ListCreateAPIView):
    permission_classes = (IsAdminOrSuperAdmin,)
    queryset = Sport.objects.all()
    serializer_class = serializer.SportSerializer

    def get_permissions(self):
        if self.request.method == "GET":
            return (permissions.AllowAny(),)
        return super().get_permissions()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(
            data=serializer.data,
            message=_("Sport created successfully"),
            code=status.HTTP_201_CREATED
        )

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        return success_response(
            data=response.data,
            message=_("Sport list retrieved successfully"),
            code=status.HTTP_200_OK
        )


class SportRetrieveUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = (IsAdminOrSuperAdmin,)
    queryset = Sport.objects.all()
    serializer_class = serializer.SportSerializer

    def get_permissions(self):
        if self.request.method == "GET":
            return (permissions.AllowAny(),)
        return super().get_permissions()

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return success_response(
            data=serializer.data,
            message=_("Sport retrieved successfully"),
            code=status.HTTP_200_OK,
        )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(
            data=serializer.data,
            message=_("Sport is updated successfully"),
            code=status.HTTP_200_OK,
        )

    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return success_response(
            message=_("Sport is deleted successfully"),
            code=status.HTTP_204_NO_CONTENT
        )


class TeamListCreateView(generics.ListCreateAPIView):
    permission_classes = (permissions.AllowAny,)
    queryset = Team.objects.all()
    serializer_class = serializer.TeamCreateSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = TeamFilter
    pagination_class = CustomPagination

    def get_serializer_class(self):
        if self.request.method == "GET":
            return serializer.TeamSerializer
        return super().get_serializer_class()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(
            data=serializer.data,
            message=_("Team created successfully"),
            code=200
        )

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return success_response(
            data=serializer.data,
            message=_("Team list retrieved successfully"),
            code=200
        )


class TeamRetrieveUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = (permissions.AllowAny,)
    queryset = Team.objects.all()
    serializer_class = serializer.TeamUpdateSerializer

    def get_serializer_class(self):
        if self.request.method == "GET":
            return serializer.TeamSerializer
        return super().get_serializer_class()

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return success_response(
            data=serializer.data,
            message=_("Team retrieved successfully"),
            code=status.HTTP_200_OK,
        )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(
            message=_("Team updated successfully"),
            data=serializer.data,
            code=status.HTTP_200_OK,
        )

    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return success_response(
            message=_("Team deleted successfully"),
            code=status.HTTP_204_NO_CONTENT
        )
