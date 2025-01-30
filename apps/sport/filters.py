from django_filters import rest_framework as filters
from django.utils.dateparse import parse_date
from django.utils.timezone import make_aware
from datetime import datetime

from shared.addons.enums import GenderChoices, UserRoles
from shared.addons.custom_logging import logger
from user.models import (
    Sportsman,
    Trainer,
    User
)

from sport.models import (
    Tournament,
    Team,
    Sport,
    Result,
)


class TournamentFilter(filters.FilterSet):
    start_time = filters.DateFilter(field_name="start_time", lookup_expr='gte')
    end_time = filters.DateFilter(field_name="end_time", lookup_expr="lte")
    sport = filters.CharFilter(method='filter_sport')

    class Meta:
        model = Tournament
        fields = ["start_time", "end_time", "sport"]
    
    def filter_sport(self, queryset, name, value):
        if value:
            queryset = queryset.filter(sport__name=value)
        return queryset

    def filter_queryset(self, queryset):
        
        # Applying the default filters (e.g., sport filter)
        queryset = super().filter_queryset(queryset)

        # Applying custom date filtering
        start_time_incoming = self.request.query_params.get("start_time", None)
        end_time_incoming = self.request.query_params.get("end_time", None)
        
        if start_time_incoming and end_time_incoming:
            parsed_start_time = parse_date(start_time_incoming)
            parsed_end_time = parse_date(end_time_incoming)
            
            start_time_aware = make_aware(datetime.combine(parsed_start_time, datetime.min.time()))
            end_time_aware = make_aware(datetime.combine(parsed_end_time, datetime.max.time()))
            
            queryset = queryset.filter(start_time__gte=start_time_aware, end_time__lte=end_time_aware)
        
        return queryset


class TeamFilter(filters.FilterSet):
    sport = filters.CharFilter(method="filter_sport")

    class Meta:
        model = Team
        fields = ["sport"]
    
    def filter_sport(self, queryset, name, value): # noqa
        return queryset.filter(sport__name=value)
