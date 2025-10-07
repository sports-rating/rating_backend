from flask import request
import pandas
from datetime import datetime

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

from apps.shared.utils.permissions import IsAdmin, IsAdminOrSuperAdmin
from apps.shared.utils.pagination import CustomPagination
from apps.shared.utils.exceptions import raise_validation_error
from apps.shared.utils.utils import (
    success_response,
    error_response
)

from apps.user.models import (
    User,
    Sportsman,
    Trainer
)

from apps.dashboard.models import (
    PrivacyPolicy,
    TermsOfCondition
)

from apps.user.serializers import (
    UsersMeSerializer
)

import apps.dashboard.serializers as serializers

from apps.dashboard.filters import (
    UserFilter,
)


class UserListView(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = serializers.UserListSerializer
    permission_classes = (
        permissions.AllowAny,
    )
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = UserFilter
    pagination_class = CustomPagination
    search_fields = [
        "first_name",
        "last_name",
        "username",
        "phone_number",
    ]

    def get_queryset(self) -> QuerySet[User]:
        queryset = User.objects.exclude(user_role__in=["ordinary", "admin", "super_admin"]).select_related(
            "sportsman_profile__trainer",
            "sportsman_profile__sport",
            "trainer_profile__sport",
            "region",
            "district",
        ).prefetch_related(
            "media",
            "results",
        )
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return success_response(
            data=serializer.data,
            message=_("Users list"),
            code=200,
        )


class AddUserAPIView(generics.GenericAPIView):
    serializer_class = serializers.AddUserSerializer
    permission_classes = [IsAdminOrSuperAdmin,]
    model = "user"
    specific_permissions = ["add_user"]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({"request": self.request})
        return context

    def post(self, request: Request, *args, **kwargs) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(
            data=serializer.data,
            message=_("User created successfully"),
            code=status.HTTP_201_CREATED,
        )


class ExportView(generics.ListAPIView):
    permission_classes = (permissions.AllowAny,)
    queryset = User.objects.all()
    serializer_class = serializers.UserExportSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = UserFilter

    def get_queryset(self):
        queryset = User.objects.select_related(
            "sportsman_profile", "trainer_profile"
        ).prefetch_related(
            "sportsman_profile__trainer",
            "sportsman_profile__sport",
            "trainer_profile__sport"
        )
        return queryset

    def get(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        serializer = self.get_serializer(queryset, many=True)
        df = pandas.DataFrame(serializer.data)

        # Create the Excel file in memory
        response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response["Content-Disposition"] = 'attachment; filename="filtered_data.xlsx"'

        with pandas.ExcelWriter(response, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Filtered Data")

        return response


class PrivacyPolicyAddListView(generics.ListCreateAPIView):
    permission_classes = (permissions.AllowAny, ) # IsAdmin
    serializer_class = serializers.PrivacyPolicySerializer
    queryset = PrivacyPolicy.objects.all()

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return success_response(
            data=serializer.data,
            message=_("List of PrivacyPolicies")
        )

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(
            data=serializer.data,
            message=_("PrivacyPolicy created successfully")
        )


class PrivacyPolicyDetailUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.AllowAny,]
    serializer_class = serializers.PrivacyPolicySerializer
    queryset = PrivacyPolicy.objects.all()

    def get_permissions(self):
        if self.request.method == "GET":
            return [permissions.AllowAny()]
        return super().get_permissions()

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return success_response(
            data=serializer.data,
            code=200,
            message=_("PrivacyPolicy instance retrieved successfully"),
        )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(
            data=serializer.data,
            message=_("PrivacyPolicy is updated successfully"),
            code=200,
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return success_response(
            message=_("PrivacyPolicy is deleted successfully"), code=204
        )

    def get_object(self):
        policy = self.queryset.filter(pk=self.kwargs["pk"]).first()
        if not policy:
            raise_validation_error(message=_("Privacy policy not found"), code=404)
        return policy


class TermsOfConditionAddListView(generics.ListCreateAPIView):
    permission_classes = [permissions.AllowAny,]
    serializer_class = serializers.TermsOfConditionSerializer
    queryset = TermsOfCondition.objects.all()

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return success_response(
            data=serializer.data,
            message=_("List of Terms of conditions")
        )

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(
            data=serializer.data, message=_("Terms of condition created successfully")
        )


class TermsOfConditionDetailUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.AllowAny,]
    serializer_class = serializers.TermsOfConditionSerializer
    queryset = TermsOfCondition.objects.all()

    def get_permissions(self):
        if self.request.method == "GET":
            return [permissions.AllowAny()]
        return super().get_permissions()

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return success_response(
            data=serializer.data,
            code=200,
            message=_("Terms of condition instance retrieved successfully"),
        )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(
            data=serializer.data,
            message=_("Terms of condition is updated successfully"),
            code=200,
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return success_response(
            message=_("Terms of condition is deleted successfully"), code=204
        )

    def get_object(self):
        condition = self.queryset.filter(pk=self.kwargs["pk"]).first()
        if not condition:
            raise_validation_error(message=_("Terms of condition not found"), code=404)
        return condition
