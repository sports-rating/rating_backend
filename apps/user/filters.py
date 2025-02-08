import uuid
from django_filters import rest_framework as filters
from datetime import datetime

from user.models import (
    Sportsman,
    User
)

class SportsmanFilter(filters.FilterSet):
    sport = filters.CharFilter(method='filter_sport')

    class Meta:
        model = User
        fields = ["sport"]
    
    def filter_sport(self, queryset, name, value): # noqa
        return queryset.filter(sportsman_profile__sport__name=value)
    

class TrainerFilter(filters.FilterSet):
    sport = filters.CharFilter(method='filter_sport')

    class Meta:
        model = User
        fields = ["sport"]

    def filter_sport(self, queryset, name, value): # noqa
        return queryset.filter(trainer_profile__sport__name=value)

