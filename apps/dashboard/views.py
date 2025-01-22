import pandas

from django.utils.translation import gettext as _, get_language
from django_filters.rest_framework import DjangoFilterBackend
from django.utils.dateparse import parse_date
from django.utils.timezone import make_aware
from django.http import HttpResponse

from rest_framework.views import APIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework import generics, permissions, status, filters as rest_framework_filters

from datetime import datetime

from shared.addons.permissions import IsAdmin
from shared.addons.pagination import CustomPagination
from shared.addons.utils import (
    success_response,
    error_response
)

from user.models import (
    User,
    Sportsman,
    Trainer,
    School
)

from dashboard.models import (
    Tournament,
    Sport,
    Team,
    PrivacyPolicy,
    TermsOfCondition
)

from user.serializers import (
    UsersMeSerializer
)

from dashboard.serializers import (
    UserListSerializer,
    TournamentCreateSerializer,
    TournamentSerializer,
    SportCreateSerializer,
    SportSerializer,
    TeamCreateSerializer,
    TeamUpdateSerializer,
    TeamSerializer,
    UserExportSerializer,
    SchoolCreateSerializer,
    SchoolSerializer,
    SchoolUpdateSerializer,
    PrivacyPolicySerializer,
    TermsOfConditionSerializer
)

from .filters import (
    UserFilter,
    TournamentFilter,
    TeamFilter,
    SchoolFilter
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

    def get_queryset(self):
        return self.queryset.exclude(user_role="ordinary")

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
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = TournamentFilter
    search_fields = ["name",]
    pagination_class = CustomPagination

    def get_serializer_class(self):
        if self.request.method == "GET":
            return TournamentSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        name = self.request.query_params.get("name")
        if name:
            return self.queryset.filter(name__icontains=name)
        return self.queryset.all()


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
    

class SportListCreateView(generics.ListCreateAPIView):
    permission_classes = (permissions.AllowAny,)
    queryset = Sport.objects.all()
    serializer_class = SportCreateSerializer

    def get_serializer_class(self):
        if self.request.method == "GET":
            return SportSerializer
        return super().get_serializer_class()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(
            data=serializer.data,
            message=_("Sport created successfully"),
            code=200
        )
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return success_response(
            data=serializer.data,
            message=_("Sport list retrieved successfully"),
            code=200
        )
    
class SportRetrieveUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = (permissions.AllowAny,)
    queryset = Sport.objects.all()
    serializer_class = SportCreateSerializer

    def get_serializer_class(self, *args, **kwargs):
        if self.request.method == "GET":
            return SportSerializer
        return super().get_serializer_class()   
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return success_response(
            data=serializer.data,
            message=_("Sport retrieved successfully"),
            code=200,
        )
    
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(
            data=serializer.data,
            message=_("Sport is updated successfully"),
            code=200,
        )
    
    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return success_response(
            message=_("Sport is deleted successfully"),
            code=204
        )
    


class TeamListCreateView(generics.ListCreateAPIView):
    permission_classes = (permissions.AllowAny,)
    queryset = Team.objects.all()
    serializer_class = TeamCreateSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = TeamFilter
    pagination_class = CustomPagination

    def get_serializer_class(self):
        if self.request.method == "GET":
            return TeamSerializer
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
    serializer_class = TeamUpdateSerializer

    def get_serializer_class(self):
        if self.request.method == "GET":
            return TeamSerializer
        return super().get_serializer_class()

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return success_response(
            data=serializer.data,
            message=_("Team retrieved successfully"),
            code=200,
        )
    
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(
            message=_("Team updated successfully"),
            data=serializer.data,
            code=200,
        )

    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return success_response(
            message=_("Team deleted successfully"),
            code=204
        )


class ExportView(generics.ListAPIView):
    permission_classes = (permissions.AllowAny,)
    queryset = User.objects.all()
    serializer_class = UserExportSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = UserFilter

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


class SchoolListCreateView(generics.ListCreateAPIView):
    permission_classes = (permissions.AllowAny,)
    queryset = School.objects.all()
    serializer_class = SchoolCreateSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = SchoolFilter
    pagination_class = CustomPagination

    def get_serializer_class(self):
        if self.request.method == "GET":
            return SchoolSerializer
        return super().get_serializer_class()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(
            data=serializer.data,
            message=_("School created successfully"),
            code=200
        )

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return success_response(
            data=serializer.data,
            message=_("School list retrieved successfully"),
            code=200
        )
    

class SchoolRetrieveUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = (permissions.AllowAny,)
    queryset = School.objects.all()
    serializer_class = SchoolUpdateSerializer

    def get_serializer_class(self):
        if self.request.method == "GET":
            return SchoolSerializer
        return super().get_serializer_class()
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return success_response(
            data=serializer.data,
            message=_("School retrieved successfully"),
            code=200,
        )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(
            data=serializer.data, 
            message=_("School updated successfully"),
            code=200,
        )

    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return success_response(
            message=_("School deleted successfully"),
            code=204
        )


class PrivacyPolicyAddListView(generics.ListCreateAPIView):
    permission_classes = (permissions.AllowAny, ) # IsAdmin
    serializer_class = PrivacyPolicySerializer
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
    serializer_class = PrivacyPolicySerializer
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
    serializer_class = TermsOfConditionSerializer
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
    serializer_class = TermsOfConditionSerializer
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
