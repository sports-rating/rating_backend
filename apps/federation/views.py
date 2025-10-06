import typing as t
from uuid import UUID
from typing import reveal_type

from django.shortcuts import render
from django.utils.translation import gettext as _, get_language
from django_filters.rest_framework import DjangoFilterBackend
from django.utils.dateparse import parse_date
from django.utils.timezone import make_aware
from django.http import HttpResponse
from django.db.models import Q, Prefetch, QuerySet
from django.contrib.auth.models import AnonymousUser

from rest_framework.views import APIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework import generics, permissions, status, filters as rest_framework_filters
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import BasePermission

from apps.shared.utils.exceptions import raise_validation_error
from apps.shared.utils.permissions import IsAdmin, IsAdminOrSuperAdmin, IsFederationAdmin
from apps.shared.utils.pagination import CustomPagination
from apps.shared.utils.utils import (
    success_response,
    error_response
)

from apps.federation.models import (
    FederationAgeGroup,
    Federation,
    AgeGroup,
    FederationDocument
)

from apps.user.models import (
    User,
    Sportsman,
    Trainer,
    UserRequest
)
from apps.sport.models import Tournament
from apps.federation.filters import (
    FederationFilter,
    FederationUserRequestFilter,
    FederationUsersFilter,
    FederationAgeGroupFilter
)

from apps.shared.utils.types import *

import apps.sport.serializers as sport_serializers
import apps.federation.serializers as serializer


class FederationListCreateAPIView(generics.ListCreateAPIView):
    permission_classes = (IsAdminOrSuperAdmin,)
    serializer_class = serializer.FederationSerializer
    queryset = Federation.objects.all()
    pagination_class = CustomPagination
    parser_classes = (FormParser, MultiPartParser)
    filter_backends = (DjangoFilterBackend, SearchFilter, OrderingFilter)
    filterset_class = FederationFilter

    def get_queryset(self) -> QuerySet[Federation]:
        return Federation.objects.prefetch_related(
            Prefetch(
                'age_group_links__age_group',
                queryset=AgeGroup.objects.select_related('sport')
            ),
            Prefetch(
                'documents',
                queryset=FederationDocument.objects.all()
            )
        )

    def get_permissions(self):
        if self.request.method == "GET":
            return [permissions.AllowAny()]
        return super().get_permissions()

    def get_serializer_context(self) -> dict[str, t.Any]:
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def create(self, request: Request, *args, **kwargs) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(
            data=serializer.data,
            message=_("Federation created successfully"),
            code=status.HTTP_201_CREATED
        )

    def list(self, request: Request, *args, **kwargs) -> Response:
        response = super().list(request, *args, **kwargs)
        return success_response(
            data=response.data,
            message=_("Federation list retrieved successfully"),
            code=status.HTTP_200_OK
        )


class FederationRetrieveUpdateDeleteAPIView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = (IsAdminOrSuperAdmin,)
    serializer_class = serializer.FederationSerializer
    queryset = Federation.objects.all()

    def get_permissions(self):
        if self.request.method == "GET":
            return [permissions.AllowAny()]
        return super().get_permissions()

    def retrieve(self, request: Request, *args, **kwargs) -> Response:
        instance: Federation = self.get_object()
        serializer = self.get_serializer(instance)
        return success_response(
            data=serializer.data,
            message=_("Federation retrieved successfully"),
            code=status.HTTP_200_OK,
        )

    def update(self, request: Request, *args, **kwargs) -> Response:
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(
            data=serializer.data,
            message=_("Federation updated successfully"),
            code=status.HTTP_200_OK,
        )

    def delete(self, request: Request, *args, **kwargs) -> Response:
        instance: Federation = self.get_object()

        # Deleting related AgeGroups first
        for link in instance.age_group_links.all():
            link.age_group.delete()

        instance.delete()
        return success_response(
            message=_("Federation deleted successfully"),
            code=status.HTTP_204_NO_CONTENT
        )


class FederationUserListAPIView(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = serializer.FederationUserListSerializer
    permission_classes = (
        permissions.IsAuthenticated,
        IsFederationAdmin,
    )
    filter_backends = [OrderingFilter, DjangoFilterBackend, SearchFilter]
    filterset_class = FederationUsersFilter
    pagination_class = CustomPagination
    search_fields = [
        "first_name",
        "last_name",
        "sportsman_profile__sport__name",
        "trainer_profile__sport__name",
        "trainer_profile__federation__name",
    ]

    def get_queryset(self) -> QuerySet[User]:
        federation_id: UUID = self.kwargs.get('pk')

        base_qs = User.objects.exclude(user_role__in=["ordinary", "admin", "super_admin"]).select_related(
            "sportsman_profile", "trainer_profile"
        ).prefetch_related(
            "sportsman_profile__trainer",
            "trainer_profile__federation"
        )

        if federation_id:
            return base_qs.filter(
                Q(trainer_profile__federation=federation_id) |
                Q(sportsman_profile__trainer__federation=federation_id) |
                Q(federations__id=federation_id)
            )
        return base_qs

    def list(self, request: Request, *args, **kwargs) -> Response:
        response: Response = super().list(request, *args, **kwargs)
        return success_response(
            data=response.data,
            message=_("Users list"),
            code=200,
        )


class RegionalFederationListCreateAPIView(generics.ListCreateAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = serializer.FederationSerializer
    queryset = Federation.objects.all()

    def get_serializer_context(self) -> dict[str, t.Any]:
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    def get_queryset(self) -> QuerySet[Federation]:
        federation_id: UUID = self.kwargs.get('pk')
        return Federation.objects.filter(parent_federation_id=federation_id).prefetch_related(
            Prefetch(
                'age_group_links__age_group',
                queryset=AgeGroup.objects.select_related('sport')
            ),
            Prefetch(
                'documents',
                queryset=FederationDocument.objects.all()
            )
        )

    def list(self, request: Request, *args, **kwargs) -> Response:
        response: Response = super().list(request, *args, **kwargs)
        return success_response(
            data=response.data,
            message=_("Regional federations list retrieved successfully"),
            code=status.HTTP_200_OK
        )

    def create(self, request: Request, *args, **kwargs) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(
            data=serializer.data,
            message=_("Regional federation created successfully"),
            code=status.HTTP_201_CREATED
        )


class FederationUserRequestListAPIView(generics.ListAPIView):
    permission_classes = (
        permissions.IsAuthenticated,
        IsFederationAdmin,
    )
    serializer_class = serializer.FederationUserRequestSerializer
    queryset = UserRequest.objects.all()
    pagination_class = CustomPagination
    filter_backends = [OrderingFilter, DjangoFilterBackend, SearchFilter]
    filterset_class = FederationUserRequestFilter
    search_fields = [
        "sender__first_name",
        "sender__last_name",
        "receivers__first_name",
        "receivers__last_name",
        "request_type",
        "message",
    ]

    def get_serializer_context(self) -> dict[str, t.Any]:
        context = super().get_serializer_context()
        context["request"] = self.request
        context["federation_id"] = self.kwargs.get('pk')
        return context

    def get_queryset(self) -> QuerySet[UserRequest]:
        federation_id: UUID = self.kwargs.get('pk')
        user: User = self.request.user  # type: ignore

        queryset: QuerySet[UserRequest] = UserRequest.objects.filter(
            receivers=user,
            federation_id=federation_id
        )
        return queryset

    def list(self, request: Request, *args, **kwargs) -> Response:
        response: Response = super().list(request, *args, **kwargs)
        return success_response(
            data=response.data,
            message=_("Federation User Request list retrieved successfully"),
            code=status.HTTP_200_OK
        )


class FederationTournamentListAPIView(generics.ListAPIView):
    permission_classes = (
        permissions.IsAuthenticated,
        IsFederationAdmin,
    )
    serializer_class = sport_serializers.TournamentSerializer
    queryset = Tournament.objects.all()
    pagination_class = CustomPagination

    def get_queryset(self) -> QuerySet[Tournament]:
        federation_id: UUID = self.kwargs.get('pk')
        return Tournament.objects.filter(federation_id=federation_id)

    def list(self, request: Request, *args, **kwargs) -> Response:
        response: Response = super().list(request, *args, **kwargs)
        return success_response(
            data=response.data,
            message=_("Federation Tournament list retrieved successfully"),
            code=status.HTTP_200_OK
        )


class FederationAgeGroupListCreateAPIView(generics.ListAPIView):
    permission_classes = (
        permissions.IsAuthenticated,
        IsFederationAdmin,
    )
    serializer_class = serializer.FederationAgeGroupSerializer
    queryset = FederationAgeGroup.objects.all()
    pagination_class = CustomPagination
    filter_backends = [OrderingFilter, DjangoFilterBackend, SearchFilter]
    filterset_class = FederationAgeGroupFilter
    search_fields = [
        "age_group__name",
        "age_group__sport__name",
    ]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return serializer.AgeGroupSerializer
        return serializer.FederationAgeGroupSerializer

    def get_serializer_context(self) -> dict[str, t.Any]:
        context = super().get_serializer_context()
        context["request"] = self.request
        context["federation_id"] = self.kwargs.get('pk')
        return context

    def get_queryset(self) -> QuerySet[FederationAgeGroup]:
        federation_id: UUID = self.kwargs.get('pk')
        return FederationAgeGroup.objects.filter(
            federation_id=federation_id
        ).select_related('age_group__sport')

    def list(self, request: Request, *args, **kwargs) -> Response:
        response: Response = super().list(request, *args, **kwargs)
        return success_response(
            data=response.data,
            message=_("Federation Age Group list retrieved successfully"),
            code=status.HTTP_200_OK
        )


class AgeGroupRetrieveUpdateDeleteAPIView(generics.RetrieveAPIView):
    permission_classes = (
        permissions.IsAuthenticated,
        IsFederationAdmin,
    )
    serializer_class = serializer.AgeGroupSerializer
    queryset = AgeGroup.objects.all()

    def get_serializer_context(self) -> dict[str, t.Any]:
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    def retrieve(self, request: Request, *args, **kwargs) -> Response:
        instance: AgeGroup = self.get_object()
        serializer = self.get_serializer(instance)
        return success_response(
            data=serializer.data,
            message=_("Age Group retrieved successfully"),
            code=status.HTTP_200_OK,
        )
