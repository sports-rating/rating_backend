import uuid
from django_filters import rest_framework as filters

from shared.addons.enums import GenderChoices, UserRoles
from shared.addons.custom_logging import logger

from education.models import (
    Education, 
    School
)

class SchoolFilter(filters.FilterSet):
    type = filters.CharFilter(method="filter_type")
    sport = filters.CharFilter(method="filter_sport")

    class Meta:
        model = School
        fields = ["type", "sport"]
    
    def filter_type(self, queryset, name, value): # noqa
        return queryset.filter(type=value)
    
    def filter_sport(self, queryset, name, value): # noqa
        return queryset.filter(sports__name=value)
    
