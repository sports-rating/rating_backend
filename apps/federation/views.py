from django.shortcuts import render

# Create your views here.
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
from apps.user.filters import (
    UserRequestFilter
)
from apps.sport.models import Tournament
import apps.sport.serializers as sport_serializers
from apps.federation.filters import (
    FederationFilter,
    FederationUserRequestFilter
)

from dashboard.filters import UserFilter
import apps.federation.serializers as serializer


class FederationListCreateAPIView(generics.ListCreateAPIView):
    permission_classes = (IsAdminOrSuperAdmin,)
    serializer_class = serializer.FederationSerializer
    queryset = Federation.objects.all()
    pagination_class = CustomPagination
    parser_classes = (FormParser, MultiPartParser)
    filter_backends = (DjangoFilterBackend, SearchFilter, OrderingFilter)
    filterset_class = FederationFilter

    def get_queryset(self):
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
            return [permissions.AllowAny(),]
        return super().get_permissions()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(
            data=serializer.data,
            message=_("Federation created successfully"),
            code=status.HTTP_201_CREATED
        )

    def list(self, request, *args, **kwargs):
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

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return success_response(
            data=serializer.data,
            message=_("Federation retrieved successfully"),
            code=status.HTTP_200_OK,
        )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        print('here')
        serializer.is_valid(raise_exception=True)
        print('passed')
        serializer.save()
        return success_response(
            data=serializer.data,
            message=_("Federation updated successfully"),
            code=status.HTTP_200_OK,
        )

    def delete(self, request, *args, **kwargs):
        instance = self.get_object()

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
    )
    filter_backends = [OrderingFilter, DjangoFilterBackend, SearchFilter]
    filterset_class = UserFilter
    pagination_class = CustomPagination

    def get_queryset(self):
        federation_id = self.kwargs.get('pk')
        user = self.request.user

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

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return success_response(
            data=serializer.data,
            message=_("Users list"),
            code=200,
        )


class RegionalFederationListCreateAPIView(generics.ListCreateAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = serializer.FederationSerializer
    queryset = Federation.objects.all()

    def get_queryset(self):
        federation_id = self.kwargs.get('pk')
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

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        return success_response(
            data=response.data,
            message=_("Regional federations list retrieved successfully"),
            code=status.HTTP_200_OK
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(
            data=serializer.data,
            message=_("Regional federation created successfully"),
            code=status.HTTP_201_CREATED
        )


class FederationUserRequestListAPIView(generics.ListAPIView):
    permission_classes = (permissions.IsAuthenticated,)
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

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        context["federation_id"] = self.kwargs.get('pk')
        return context

    def get_queryset(self):
        request_type = "received"
        federation_id = self.kwargs.get('pk')
        queryset = UserRequest.objects.filter(
            receivers=self.request.user,
            federation_id=federation_id
        )
        print(queryset)
        return queryset

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        return success_response(
            data=response.data,
            message=_("Federation User Request list retrieved successfully"),
            code=status.HTTP_200_OK
        )


class FederationTournamentListAPIView(generics.ListAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = sport_serializers.TournamentSerializer
    queryset = Tournament.objects.all()
    pagination_class = CustomPagination

    def get_queryset(self):
        federation_id = self.kwargs.get('pk')
        return Tournament.objects.filter(federation_id=federation_id)

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        return success_response(
            data=response.data,
            message=_("Federation Tournament list retrieved successfully"),
            code=status.HTTP_200_OK
        )
