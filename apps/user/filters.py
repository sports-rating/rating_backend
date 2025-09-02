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
    UserRequestStatus,
    UserRequestTypes
)
from apps.shared.utils.filters import BaseFilterSet
from apps.shared.models import (
    District,
    Neighborhood
)
from apps.federation.models import Federation


class SportsmanFilter(BaseFilterSet):
    # sport = filters.CharFilter(method='filter_sport')
    sport = filters.CharFilter(field_name="sportsman_profile__sport__id")

    class Meta:
        model = User
        fields = ["sport"]

    def filter_sport(self, queryset, name, value): # noqa
        return queryset.filter(sportsman_profile__sport__name=value)


class TrainerFilter(BaseFilterSet):
    # sport = filters.CharFilter(method='filter_sport')
    sport = filters.CharFilter(field_name="trainer_profile__sport__id")
    verified = filters.BooleanFilter(field_name='trainer_profile__is_trainer_verified')

    class Meta:
        model = User
        fields = ["sport", "verified"]

    def filter_sport(self, queryset, name, value): # noqa
        return queryset.filter(trainer_profile__sport__name=value)


class UserNotificationFilter(BaseFilterSet):
    is_read = filters.BooleanFilter(field_name="is_read")

    class Meta:
        model = UserNotification
        fields = ["is_read", "start_created_time", "end_created_time", "start_updated_time", "end_updated_time"]


class UserRequestFilter(BaseFilterSet):
    REQUEST_ROLE_MAPPING = {
        "sportsman_trainer": UserRequestTypes.SPORTSMAN_TRAINER_REQUEST.value,
        "sportsman_result": UserRequestTypes.SPORTSMAN_RESULT_VERIFICATION_REQUEST.value
    }

    status = filters.ChoiceFilter(choices=UserRequestStatus.choices())
    date = filters.DateFilter(field_name="created_time", lookup_expr="date")
    request_type = filters.CharFilter(method='filter_request_type')

    class Meta:
        model = UserRequest
        fields = [
            "status",
            "date"
        ]

    def filter_request_type(self, queryset, name, value):
        mapped_value = self.REQUEST_ROLE_MAPPING.get(value)
        print(mapped_value)
        if mapped_value:
            return queryset.filter(request_type=mapped_value)
        return queryset


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
