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

from apps.shared.utils.permissions import IsAdmin, IsAdminOrSuperAdmin
from apps.shared.utils.pagination import CustomPagination
from apps.shared.utils.utils import (
    success_response,
    error_response
)

from apps.education.models import (
    Education,
    School
)

from apps.education.serializers import (
    EducationCreateSerializer,
    EducationSerializer,
    SchoolSerializer,
)

from apps.education.filters import (
    SchoolFilter
)


class EducationRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = (permissions.AllowAny, )
    queryset = Education.objects.all()
    serializer_class = EducationCreateSerializer

    def get_serializer_class(self):
        if self.request.method == "GET":
            return EducationSerializer
        return super().get_serializer_class()

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return success_response(
            data=serializer.data,
            message=_("Education retrieved successfully"),
            code=status.HTTP_200_OK,
        )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(
            data=serializer.data,
            message=_("Education updated successfully"),
            code=status.HTTP_200_OK,
        )

    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return success_response(
            message=_("Education deleted successfully"),
            code=status.HTTP_204_NO_CONTENT
        )


class SchoolListCreateView(generics.ListCreateAPIView):
    permission_classes = (IsAdminOrSuperAdmin,)
    queryset = School.objects.all()
    serializer_class = SchoolSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = SchoolFilter
    pagination_class = CustomPagination

    def get_permissions(self):
        if self.request.method == "GET":
            return (permissions.AllowAny(),)
        return super().get_permissions()

    def get_queryset(self):
        return self.queryset.prefetch_related("sports")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(
            data=serializer.data,
            message=_("School created successfully"),
            code=status.HTTP_201_CREATED
        )

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        return success_response(
            data=response.data,
            message=_("School list retrieved successfully"),
            code=status.HTTP_200_OK
        )


class SchoolRetrieveUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = (permissions.AllowAny,)
    queryset = School.objects.all()
    serializer_class = SchoolSerializer

    def get_permissions(self):
        if self.request.method == "GET":
            return (permissions.AllowAny(),)
        return super().get_permissions()

    def get_queryset(self):
        return self.queryset.prefetch_related("sports")

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return success_response(
            data=serializer.data,
            message=_("School retrieved successfully"),
            code=status.HTTP_200_OK,
        )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(
            data=serializer.data,
            message=_("School updated successfully"),
            code=status.HTTP_200_OK,
        )

    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return success_response(
            message=_("School deleted successfully"),
            code=status.HTTP_204_NO_CONTENT
        )
