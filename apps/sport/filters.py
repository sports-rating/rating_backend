from datetime import datetime

from django_filters import rest_framework as filters
from django.utils.dateparse import parse_date
from django.utils.timezone import make_aware
from django.db.models import F, Q

from apps.shared.utils import enums
from apps.shared.utils.logging import logger
from apps.user.models import (
    Sportsman,
    Trainer,
    User
)

from apps.sport.models import (
    Tournament,
    Team,
    Sport,
    SportInstitution,
    SportInstitutionRequest
)


class TournamentFilter(filters.FilterSet):
    start_time = filters.DateFilter(field_name="start_time", lookup_expr='gte')
    end_time = filters.DateFilter(field_name="end_time", lookup_expr="lte")
    sport = filters.CharFilter(method='filter_sport')
    federation = filters.CharFilter(field_name="federation__id")

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

        # Applying custom year filtering
        start_year = self.request.query_params.get("start_year", None)
        end_year = self.request.query_params.get("end_year", None)

        if start_year and end_year:
            try:
                start_year = int(start_year)
                end_year = int(end_year)
                queryset = queryset.filter(year__gte=start_year, year__lte=end_year)
            except ValueError:
                pass  # Ignore invalid year values

        return queryset

class TeamFilter(filters.FilterSet):
    sport = filters.CharFilter(method="filter_sport")

    class Meta:
        model = Team
        fields = ["sport"]

    def filter_sport(self, queryset, name, value): # noqa
        return queryset.filter(sport__name=value)


class SportInstitutionFilter(filters.FilterSet):
    type = filters.ChoiceFilter(field_name="type", choices=enums.SportInstitutionChoices.choices())
    sports = filters.CharFilter(field_name="sports__id")
    federation = filters.CharFilter(field_name="federation__id")
    region = filters.CharFilter(field_name="region__id")

    class Meta:
        model = SportInstitution
        fields = ["type", "sports", "federation", "region"]


class SportInstitutionUsersFilter(filters.FilterSet):
    user_role = filters.ChoiceFilter(choices=enums.UserRoles.choices())
    sport = filters.CharFilter(method="filter_sport")
    region = filters.CharFilter(field_name='region__id')
    district = filters.CharFilter(field_name='district__id')
    gender = filters.ChoiceFilter(choices=enums.GenderChoices.choices())

    class Meta:
        model = User
        fields = ["sport", "region", "district", "gender"]

    def filter_sport(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(
            Q(sportsman_profile__sport__id=value) |
            Q(trainer_profile__sport__id=value)
        )


class SportInstitutionRequestFilter(filters.FilterSet):
    status = filters.ChoiceFilter(field_name="status", choices=enums.SportInstitutionRequestStatus.choices())

    class Meta:
        model = SportInstitutionRequest
        fields = ["status"]
