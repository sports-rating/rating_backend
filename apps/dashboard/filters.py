import uuid
from django_filters import rest_framework as filters
from django.utils.dateparse import parse_date
from django.utils.timezone import make_aware
from datetime import datetime

from shared.addons.enums import GenderChoices, UserRoles
from user.models import (
    Sportsman,
    Trainer,
    User,
    School
)

from dashboard.models import (
    Tournament,
    Team
)

class UserFilter(filters.FilterSet):
    user_role = filters.CharFilter(method="filter_user_role")
    start_time = filters.CharFilter(method="filter_start_time")
    end_time = filters.CharFilter(method="filter_end_time")
    sport = filters.CharFilter(method='filter_sport')

    class Meta:
        model = User
        fields = ["user_role", "start_time", "end_time", "sport"]
    
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
    
    def filter_sport(self, queryset, name, value):
        user_role = self.request.query_params.get("user_role")
        sport = value

        if user_role:
            queryset = queryset.filter(user_role=user_role)
        if sport:
            if user_role == "sportsman":
                queryset = queryset.filter(sportsman_profile__sport__name=sport)
            elif user_role == "trainer":
                queryset = queryset.filter(trainer_profile__sport__name=sport)
        
        return queryset
        

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


class SchoolFilter(filters.FilterSet):
    type = filters.CharFilter(method="filter_type")

    class Meta:
        model = School
        fields = ["type"]
    
    def filter_type(self, queryset, name, value): # noqa
        return queryset.filter(type=value)
    