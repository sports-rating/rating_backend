import uuid
from django_filters import rest_framework as filters
from django.utils.dateparse import parse_date
from django.utils.timezone import make_aware
from datetime import datetime

from shared.addons.enums import GenderChoices, UserRoles
from user.models import (
    Sportsman,
    Trainer,
    User
)

class UserFilter(filters.FilterSet):
    user_role = filters.CharFilter(method="filter_user_role")
    start_time = filters.CharFilter(method="filter_start_time")
    end_time = filters.CharFilter(method="filter_end_time")

    class Meta:
        model = User
        fields = ["user_role", "start_time", "end_time"]
    
    def filter_user_role(self, queryset, name, value):  # noqa
        if value == "sportsman":
            return queryset.filter(sportsman_profile__isnull=False)
        elif value == "trainer":
            return queryset.filter(trainer_profile__isnull=False)
        elif value == "ordinary":
            return queryset.filter(sportsman_profile__isnull=True, trainer_profile__isnull=True)
        return queryset
    
    def filter_start_time(self, queryset, name, value):
        if value:
            value = parse_date(value)
            if value:
                start_date = make_aware(datetime.combine(value, datetime.min.time()))
                return queryset.filter(created_time__gte=start_date)
        

    def filter_end_time(self, queryset, name, value):
        if value:
            value = parse_date(value)
            if value:
                end_date = make_aware(datetime.combine(value, datetime.min.time()))
                return queryset.filter(created_time__lte=end_date)
       
        