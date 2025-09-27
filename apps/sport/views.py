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

from apps.shared.utils.permissions import IsAdmin, IsAdminOrSuperAdmin
from apps.shared.utils.pagination import CustomPagination
from apps.shared.utils.utils import (
    success_response,
    error_response
)
from apps.shared.utils.exceptions import raise_validation_error

from apps.sport.models import (
    Sport,
    Result,
    Tournament,
    Team,
    School
)

import apps.sport.serializers as serializers

from apps.sport.filters import (
    TournamentFilter,
    TeamFilter,
    SchoolFilter
)


class ResultRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = (permissions.AllowAny,)
    queryset = Result.objects.all().select_related('trainer', 'archived_trainer', 'tournament')
    serializer_class = serializers.ResultCreateSerializer

    def get_serializer_class(self):
        if self.request.method == "GET":
            return serializers.ResultSerializer
        return super().get_serializer_class()

    def retrieve(self, request: Request, *args, **kwargs) -> Response:
        instance: Result = self.get_object()
        serializer: serializers.ResultSerializer = self.get_serializer(instance)
        return success_response(
            data=serializer.data,
            message=_("Result retrieved successfully"),
            code=200,
        )

    def update(self, request: Request, *args, **kwargs) -> Response:
        instance: Result = self.get_object()
        serializer: serializers.ResultCreateSerializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(
            data=serializer.data,
            message=_("Result updated successfully"),
            code=200,
        )

    def delete(self, request: Request, *args, **kwargs) -> Response:
        instance: Result = self.get_object()
        instance.delete()
        return success_response(
            message=_("Result deleted successfully"),
            code=204
        )


class TournamentListCreateView(generics.ListCreateAPIView):
    permission_classes = (IsAdminOrSuperAdmin,)
    queryset = Tournament.objects.all()
    serializer_class = serializers.TournamentSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = TournamentFilter
    search_fields = ["name",]
    pagination_class = CustomPagination

    def get_queryset(self) -> QuerySet[Tournament]:
        name: str = self.request.query_params.get("name")
        if name:
            return self.queryset.select_related("sport").filter(name__icontains=name)
        return self.queryset.select_related("sport")

    def get_permissions(self):
        if self.request.method == "GET":
            return (permissions.AllowAny(),)
        return super().get_permissions()

    def create(self, request: Request, *args, **kwargs) -> Response:
        serializer: serializers.TournamentSerializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(
            data=serializer.data,
            message=_("Tournament created successfully"),
            code=status.HTTP_201_CREATED
        )

    def list(self, request: Request, *args, **kwargs) -> Response:
        queryset: QuerySet[Tournament] = self.filter_queryset(self.get_queryset())
        serializer: serializers.TournamentSerializer = self.get_serializer(queryset, many=True)
        return success_response(
            data=serializer.data,
            message=_("Tournament list retrieved successfully"),
            code=status.HTTP_200_OK
        )


class TournamentRetrieveUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = (IsAdminOrSuperAdmin,)
    queryset = Tournament.objects.all()
    serializer_class = serializers.TournamentSerializer

    def get_queryset(self) -> QuerySet[Tournament]:
        return self.queryset.select_related("sport")

    def get_permissions(self):
        if self.request.method == "GET":
            return (permissions.AllowAny(),)
        return super().get_permissions()

    def get_object(self) -> Tournament:
        tournament_id: UUID = self.kwargs.get("pk")
        tournament: Tournament = self.queryset.filter(tournament_id=tournament_id).first()
        if not tournament:
            raise_validation_error(message=_("Tournament not found"), code=status.HTTP_404_NOT_FOUND)
        return tournament

    def retrieve(self, request: Request, *args, **kwargs) -> Response:
        instance: Tournament = self.get_object()
        serializer: serializers.TournamentSerializer = self.get_serializer(instance)
        return success_response(
            data=serializer.data,
            message=_("Tournament retrieved successfully"),
            code=status.HTTP_200_OK,
        )

    def update(self, request: Request, *args, **kwargs) -> Response:
        instance: Tournament = self.get_object()
        serializer: serializers.TournamentSerializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(
            message=_("Tournament is updated successfully"),
            data=serializer.data,
            code=status.HTTP_200_OK,
        )

    def delete(self, request: Request, *args, **kwargs) -> Response:
        instance: Tournament = self.get_object()
        instance.delete()
        return success_response(
            message=_("Tournament is deleted successfully"),
            code=status.HTTP_204_NO_CONTENT
        )


class SportListCreateView(generics.ListCreateAPIView):
    permission_classes = (IsAdminOrSuperAdmin,)
    queryset = Sport.objects.all()
    serializer_class = serializers.SportSerializer

    def get_permissions(self):
        if self.request.method == "GET":
            return (permissions.AllowAny(),)
        return super().get_permissions()

    def create(self, request: Request, *args, **kwargs) -> Response:
        serializer: serializers.SportSerializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(
            data=serializer.data,
            message=_("Sport created successfully"),
            code=status.HTTP_201_CREATED
        )

    def list(self, request: Request, *args, **kwargs) -> Response:
        response: Response = super().list(request, *args, **kwargs)
        return success_response(
            data=response.data,
            message=_("Sport list retrieved successfully"),
            code=status.HTTP_200_OK
        )


class SportRetrieveUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = (IsAdminOrSuperAdmin,)
    queryset = Sport.objects.all()
    serializer_class = serializers.SportSerializer

    def get_permissions(self):
        if self.request.method == "GET":
            return (permissions.AllowAny(),)
        return super().get_permissions()

    def get_object(self) -> Sport:
        sport_id: UUID = self.kwargs.get("pk")
        sport: Sport = self.queryset.filter(sport_id=sport_id).first()
        if not sport:
            raise_validation_error(message=_("Sport not found"), code=status.HTTP_404_NOT_FOUND)
        return sport

    def retrieve(self, request: Request, *args, **kwargs) -> Response:
        instance: Sport = self.get_object()
        serializer: serializers.SportSerializer = self.get_serializer(instance)
        return success_response(
            data=serializer.data,
            message=_("Sport retrieved successfully"),
            code=status.HTTP_200_OK,
        )

    def update(self, request: Request, *args, **kwargs) -> Response:
        instance: Sport = self.get_object()
        serializer: serializers.SportSerializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(
            data=serializer.data,
            message=_("Sport is updated successfully"),
            code=status.HTTP_200_OK,
        )

    def delete(self, request: Request, *args, **kwargs) -> Response:
        instance: Sport = self.get_object()
        instance.delete()
        return success_response(
            message=_("Sport is deleted successfully"),
            code=status.HTTP_204_NO_CONTENT
        )


class TeamListCreateView(generics.ListCreateAPIView):
    permission_classes = (permissions.AllowAny,)
    queryset = Team.objects.all()
    serializer_class = serializers.TeamCreateSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = TeamFilter
    pagination_class = CustomPagination

    def get_serializer_class(self):
        if self.request.method == "GET":
            return serializers.TeamSerializer
        return super().get_serializer_class()

    def create(self, request: Request, *args, **kwargs) -> Response:
        serializer: serializers.TeamCreateSerializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(
            data=serializer.data,
            message=_("Team created successfully"),
            code=200
        )

    def list(self, request: Request, *args, **kwargs) -> Response:
        queryset: QuerySet[Team] = self.filter_queryset(self.get_queryset())
        serializer: serializers.TeamSerializer = self.get_serializer(queryset, many=True)
        return success_response(
            data=serializer.data,
            message=_("Team list retrieved successfully"),
            code=200
        )


class TeamRetrieveUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = (permissions.AllowAny,)
    queryset = Team.objects.all()
    serializer_class = serializers.TeamUpdateSerializer

    def get_serializer_class(self):
        if self.request.method == "GET":
            return serializers.TeamSerializer
        return super().get_serializer_class()

    def get_object(self) -> Team:
        team_id: UUID = self.kwargs.get("pk")
        team: Team = self.queryset.filter(team_id=team_id).first()
        if not team:
            raise_validation_error(message=_("Team not found"), code=status.HTTP_404_NOT_FOUND)
        return team

    def retrieve(self, request: Request, *args, **kwargs) -> Response:
        instance: Team = self.get_object()
        serializer: serializers.TeamSerializer = self.get_serializer(instance)
        return success_response(
            data=serializer.data,
            message=_("Team retrieved successfully"),
            code=status.HTTP_200_OK,
        )

    def update(self, request: Request, *args, **kwargs) -> Response:
        instance: Team = self.get_object()
        serializer: serializers.TeamUpdateSerializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(
            message=_("Team updated successfully"),
            data=serializer.data,
            code=status.HTTP_200_OK,
        )

    def delete(self, request: Request, *args, **kwargs) -> Response:
        instance: Team = self.get_object()
        instance.delete()
        return success_response(
            message=_("Team deleted successfully"),
            code=status.HTTP_204_NO_CONTENT
        )


class SchoolListCreateView(generics.ListCreateAPIView):
    permission_classes = (IsAdminOrSuperAdmin,)
    queryset = School.objects.all()
    serializer_class = serializers.SchoolSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = SchoolFilter
    pagination_class = CustomPagination

    def get_permissions(self):
        if self.request.method == "GET":
            return (permissions.AllowAny(),)
        return super().get_permissions()

    def get_queryset(self) -> QuerySet[School]:
        return self.queryset.prefetch_related("sports")

    def create(self, request: Request, *args, **kwargs) -> Response:
        serializer: serializers.SchoolSerializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(
            data=serializer.data,
            message=_("School created successfully"),
            code=status.HTTP_201_CREATED
        )

    def list(self, request: Request, *args, **kwargs) -> Response:
        response: Response = super().list(request, *args, **kwargs)
        return success_response(
            data=response.data,
            message=_("School list retrieved successfully"),
            code=status.HTTP_200_OK
        )


class SchoolRetrieveUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = (permissions.AllowAny,)
    queryset = School.objects.all()
    serializer_class = serializers.SchoolSerializer

    def get_permissions(self):
        if self.request.method == "GET":
            return (permissions.AllowAny(),)
        return super().get_permissions()

    def get_queryset(self) -> QuerySet[School]:
        return self.queryset.prefetch_related("sports")

    def get_object(self) -> School:
        school_id: UUID = self.kwargs.get("pk")
        school: School = self.queryset.filter(id=school_id).first()
        if not school:
            raise_validation_error(message=_("School not found"), code=status.HTTP_404_NOT_FOUND)
        return school

    def retrieve(self, request: Request, *args, **kwargs) -> Response:
        instance: School = self.get_object()
        serializer: serializers.SchoolSerializer = self.get_serializer(instance)
        return success_response(
            data=serializer.data,
            message=_("School retrieved successfully"),
            code=status.HTTP_200_OK,
        )

    def update(self, request: Request, *args, **kwargs) -> Response:
        instance: School = self.get_object()
        serializer: serializers.SchoolSerializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(
            data=serializer.data,
            message=_("School updated successfully"),
            code=status.HTTP_200_OK,
        )

    def delete(self, request: Request, *args, **kwargs) -> Response:
        instance: School = self.get_object()
        instance.delete()
        return success_response(
            message=_("School deleted successfully"),
            code=status.HTTP_204_NO_CONTENT
        )
