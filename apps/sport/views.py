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
from apps.shared.utils import enums
from apps.shared.utils.exceptions import raise_validation_error

from apps.sport.models import (
    Sport,
    Tournament,
    Team,
    SportInstitution,
    SportInstitutionRequest
)
from apps.user.models import User

import apps.sport.serializers as serializers
import apps.user.serializers as user_serializers

from apps.sport.filters import (
    TournamentFilter,
    TeamFilter,
    SportInstitutionFilter,
    SportInstitutionUsersFilter,
    SportInstitutionRequestFilter
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
        sport: Sport = self.queryset.filter(pk=sport_id).first()
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


class SportInstitutionListCreateView(generics.ListCreateAPIView):
    permission_classes = (IsAdminOrSuperAdmin,)
    queryset = SportInstitution.objects.all()
    serializer_class = serializers.SportInstitutionSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = SportInstitutionFilter
    pagination_class = CustomPagination

    def get_permissions(self):
        if self.request.method == "GET":
            return (permissions.AllowAny(),)
        return super().get_permissions()

    def get_queryset(self) -> QuerySet[SportInstitution]:
        return self.queryset.select_related(
            "region",
            "district",
        ).prefetch_related(
            "sports",
            "institution_trainer_work_places",
            "media",
        ).order_by("created_time")

    def create(self, request: Request, *args, **kwargs) -> Response:
        serializer: serializers.SportInstitutionSerializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(
            data=serializer.data,
            message=_("Sport institution created successfully"),
            code=status.HTTP_201_CREATED
        )

    def list(self, request: Request, *args, **kwargs) -> Response:
        response: Response = super().list(request, *args, **kwargs)
        return success_response(
            data=response.data,
            message=_("Sport institution list retrieved successfully"),
            code=status.HTTP_200_OK
        )


class SportInstitutionRetrieveUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = (permissions.AllowAny,)
    queryset = SportInstitution.objects.all()
    serializer_class = serializers.SportInstitutionSerializer

    def get_permissions(self):
        if self.request.method == "GET":
            return (permissions.AllowAny(),)
        return super().get_permissions()

    def get_queryset(self) -> QuerySet[SportInstitution]:
        return self.queryset.prefetch_related("sports")

    def get_object(self) -> SportInstitution:
        sport_institution_id: UUID = self.kwargs.get("pk")
        sport_institution: SportInstitution = self.queryset.filter(id=sport_institution_id).first()
        if not sport_institution:
            raise_validation_error(message=_("Sport institution not found"), code=status.HTTP_404_NOT_FOUND)
        return sport_institution

    def retrieve(self, request: Request, *args, **kwargs) -> Response:
        instance: SportInstitution = self.get_object()
        serializer: serializers.SportInstitutionSerializer = self.get_serializer(instance)
        return success_response(
            data=serializer.data,
            message=_("School retrieved successfully"),
            code=status.HTTP_200_OK,
        )

    def update(self, request: Request, *args, **kwargs) -> Response:
        instance: SportInstitution = self.get_object()
        serializer: serializers.SportInstitutionSerializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(
            data=serializer.data,
            message=_("Sport institution updated successfully"),
            code=status.HTTP_200_OK,
        )

    def delete(self, request: Request, *args, **kwargs) -> Response:
        instance: SportInstitution = self.get_object()
        instance.delete()
        return success_response(
            message=_("Sport institution deleted successfully"),
            code=status.HTTP_204_NO_CONTENT
        )


class SportInstitutionRequestListCreateView(generics.ListCreateAPIView):
    permission_classes = (permissions.AllowAny,)
    queryset = SportInstitutionRequest.objects.all()
    serializer_class = serializers.SportInstitutionRequestSerializer
    pagination_class = CustomPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = SportInstitutionRequestFilter
    search_fields = [
        "manager_first_name",
        "manager_last_name",
        "manager_phone_number",
        "school_name",
        "school_phone_number"
    ]

    def get_queryset(self) -> QuerySet[SportInstitutionRequest]:
        return self.queryset.select_related("processed_by")

    def get_permissions(self):
        if self.request.method == "GET":
            return (IsAdminOrSuperAdmin(),)
        return super().get_permissions()

    def create(self, request: Request, *args, **kwargs) -> Response:
        serializer: serializers.SportInstitutionRequestSerializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(
            data=serializer.data,
            message=_("Sport institution request created successfully"),
            code=status.HTTP_201_CREATED
        )

    def list(self, request: Request, *args, **kwargs) -> Response:
        response: Response = super().list(request, *args, **kwargs)
        return success_response(
            data=response.data,
            message=_("Sport institution request list retrieved successfully"),
            code=status.HTTP_200_OK
        )


class SportInstitutionRequestRetrieveUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = (IsAdminOrSuperAdmin,)
    queryset = SportInstitutionRequest.objects.all()
    serializer_class = serializers.SportInstitutionRequestSerializer

    def get_object(self) -> SportInstitutionRequest:
        request_id: UUID = self.kwargs.get("pk")
        request: SportInstitutionRequest = self.queryset.filter(id=request_id).first()
        if not request:
            raise_validation_error(message=_("Sport institution request not found"), code=status.HTTP_404_NOT_FOUND)
        return request

    def retrieve(self, request: Request, *args, **kwargs) -> Response:
        instance: SportInstitutionRequest = self.get_object()
        serializer: serializers.SportInstitutionRequestSerializer = self.get_serializer(instance)
        return success_response(
            data=serializer.data,
            message=_("Sport institution request retrieved successfully"),
            code=status.HTTP_200_OK,
        )

    def update(self, request: Request, *args, **kwargs) -> Response:
        instance: SportInstitutionRequest = self.get_object()
        serializer: serializers.SportInstitutionRequestSerializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(
            data=serializer.data,
            message=_("Sport institution request updated successfully"),
            code=status.HTTP_200_OK,
        )

    def delete(self, request: Request, *args, **kwargs) -> Response:
        instance: SportInstitutionRequest = self.get_object()
        instance.delete()
        return success_response(
            message=_("Sport institution request deleted successfully"),
            code=status.HTTP_204_NO_CONTENT
        )


class SportInstitutionUsersListView(generics.ListAPIView):
    permission_classes = (permissions.AllowAny,)
    queryset = User.objects.all()
    serializer_class = serializers.SportInstitutionUsersSerializer
    pagination_class = CustomPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = SportInstitutionUsersFilter
    search_fields = ["first_name", "last_name", "username", "phone_number"]

    def get_queryset(self) -> QuerySet[User]:
        sport_institution_id: UUID = self.kwargs.get("pk")

        base_qs = User.objects.exclude(user_role__in=[
            enums.UserRoles.SUPER_ADMIN.value,
            enums.UserRoles.ADMIN.value,
            enums.UserRoles.ORDINARY.value,
        ]).select_related(
            "sportsman_profile",
            "trainer_profile",
            "region",
            "district",
        ).prefetch_related(
            "media",
            "user_educations",
            "sportsman_profile__trainer",
            "trainer_profile__federation",
            "trainer_profile__work_places",
        )

        if sport_institution_id:
            return base_qs.filter(
                Q(trainer_profile__work_places__sport_institution__id=sport_institution_id) |
                Q(user_educations__sport_institution__id=sport_institution_id)
            ).distinct()

        return base_qs

    def list(self, request: Request, *args, **kwargs) -> Response:
        response: Response = super().list(request, *args, **kwargs)
        return success_response(
            data=response.data,
            message=_("Sport institution users retrieved successfully"),
            code=status.HTTP_200_OK
        )
