import uuid
from django_filters import rest_framework as filters
from datetime import datetime

from apps.user.models import (
    Sportsman,
    UserNotification,
    User,
    UserRequest
)
from apps.shared.utils.enums import (
    UserRequestStatus
)
from apps.shared.utils.filters import BaseFilterSet
from apps.shared.models import (
    District,
    Neighborhood
)
from apps.federation.models import Federation


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


class UserRequestFilter(BaseFilterSet):
    status = filters.ChoiceFilter(choices=UserRequestStatus.choices())
    date = filters.DateFilter(field_name="created_time", lookup_expr="date")
    federation = filters.ModelChoiceFilter(
        queryset=Federation.objects.all(),
        field_name="receivers__federations"
    )

    class Meta:
        model = UserRequest
        fields = [
            "status",
            "date",
            "federation"
        ]


class DistrictFilter(BaseFilterSet):
    region = filters.CharFilter(field_name="region__id")

    class Meta:
        model = District
        fields = ["region", "start_created_time", "end_created_time", "start_updated_time", "end_updated_time"]


class NeighborhoodFilter(BaseFilterSet):
    district = filters.CharFilter(field_name="district__id")

    class Meta:
        model = Neighborhood
        fields = ["district", "start_created_time", "end_created_time", "start_updated_time", "end_updated_time"]
