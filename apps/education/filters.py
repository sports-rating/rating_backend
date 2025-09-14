import uuid
from django_filters import rest_framework as filters

from apps.shared.utils.enums import GenderChoices, UserRoles
from apps.shared.utils.logging import logger

from apps.education.models import (
    Education,
    School
)

class SchoolFilter(filters.FilterSet):
    type = filters.CharFilter(method="filter_type")
    sport = filters.CharFilter(method="filter_sport")
    federation = filters.CharFilter(field_name="federation__id")

    class Meta:
        model = School
        fields = ["type", "sport"]

    def filter_type(self, queryset, name, value): # noqa
        return queryset.filter(type=value)

    def filter_sport(self, queryset, name, value): # noqa
        return queryset.filter(sports__name=value)
