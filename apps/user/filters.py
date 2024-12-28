import uuid
from django_filters import rest_framework as filters
from datetime import datetime

from user.models import (
    Sportsman,
    User
)

class SportsmanFilter(filters.FilterSet):
    sport = filters.CharFilter()

    class Meta:
        model = User
        fields = ["sport"]
    
    def filter_queryset(self, queryset):
        return queryset.filter()


