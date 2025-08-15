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
    Trainer
)
from apps.dashboard.serializers import (
    UserListSerializer
)
from dashboard.filters import UserFilter
import apps.federation.serializers as serializer


class FederationListCreateAPIView(generics.ListCreateAPIView):
    permission_classes = (IsAdminOrSuperAdmin,)
    serializer_class = serializer.FederationSerializer
    queryset = Federation.objects.all()
    pagination_class = CustomPagination
    parser_classes = (FormParser, MultiPartParser)

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


class UserListAPIView(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserListSerializer
    permission_classes = (
        permissions.IsAuthenticated,
    )
    filter_backends = [DjangoFilterBackend]
    filterset_class = UserFilter
    pagination_class = CustomPagination

    def get_queryset(self):
        user = self.request.user
        federation = getattr(user, 'federation', None)

        base_qs = User.objects.exclude(user_role__in=["ordinary", "admin"]).select_related(
            "sportsman_profile", "trainer_profile"
        ).prefetch_related(
            "sportsman_profile__trainer",
            "trainer_profile__federation"
        )

        if federation:
            return base_qs.filter(
                Q(trainer_profile__federation=federation) |
                Q(sportsman_profile__trainer__federation=federation)
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
