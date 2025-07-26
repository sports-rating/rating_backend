import uuid
from django_filters import rest_framework as filters
from datetime import datetime

from apps.user.models import (
    Sportsman,
    UserNotification,
    User,
)
from apps.shared.utils.filters import BaseFilterSet


class SportsmanFilter(BaseFilterSet):
    sport = filters.CharFilter(method='filter_sport')

    class Meta:
        model = User
        fields = ["sport"]
    
    def filter_sport(self, queryset, name, value): # noqa
        return queryset.filter(sportsman_profile__sport__name=value)
    

class TrainerFilter(BaseFilterSet):
    sport = filters.CharFilter(method='filter_sport')

    class Meta:
        model = User
        fields = ["sport"]

    def filter_sport(self, queryset, name, value): # noqa
        return queryset.filter(trainer_profile__sport__name=value)


class UserNotificationFilter(BaseFilterSet):
    is_read = filters.BooleanFilter(field_name="is_read")

    class Meta:
        model = UserNotification
        fields = ["is_read", "start_created_time", "end_created_time", "start_updated_time", "end_updated_time"]
