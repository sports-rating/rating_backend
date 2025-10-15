from datetime import datetime

from django_filters import rest_framework as filters
from django.utils.dateparse import parse_date
from django.utils.timezone import make_aware

from apps.shared.utils.enums import GenderChoices, UserRoles
from apps.shared.utils.logging import logger

from apps.user.models import (
    Sportsman,
    Trainer,
    User,
    UserRequest
)
from apps.shared.utils.filters import BaseFilterSet
from apps.shared.utils import enums


class UserFilter(filters.FilterSet):
    user_role = filters.ChoiceFilter(choices=UserRoles.choices())
    start_time = filters.CharFilter(method="filter_start_time")
    end_time = filters.CharFilter(method="filter_end_time")
    sport = filters.CharFilter(method='filter_sport')
    region = filters.CharFilter(field_name='region__id')
    district = filters.CharFilter(field_name='district__id')
    federation = filters.CharFilter(field_name='trainer_profile__federation__id')

    class Meta:
        model = User
        fields = [
            "user_role",
            "start_time",
            "end_time",
            "sport",
            "region",
            "district",
            "federation"
        ]

    def filter_start_time(self, queryset, name, value):
        if value:
            value = parse_date(value)
            if value:
                start_date = make_aware(datetime.combine(value, datetime.min.time()))
                logger.info(f"Start time filtering - {start_date}")
                return queryset.filter(created_time__gte=start_date)

    def filter_end_time(self, queryset, name, value):
        if value:
            value = parse_date(value)
            if value:
                end_date = make_aware(datetime.combine(value, datetime.min.time()))
                logger.info(f"End time filtering - {end_date}")
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


class UserRequestFilter(BaseFilterSet):
    REQUEST_ROLE_MAPPING = {
        "sportsman_trainer": enums.UserRequestTypes.SPORTSMAN_TRAINER_REQUEST.value,
        "trainer_federation": enums.UserRequestTypes.TRAINER_FEDERATION_REQUEST.value,
        "sportsman_result": enums.UserRequestTypes.SPORTSMAN_RESULT_VERIFICATION_REQUEST.value,
        "trainer_workplace": enums.UserRequestTypes.TRAINER_WORKPLACE_VERIFICATION_REQUEST.value
    }

    status = filters.ChoiceFilter(choices=enums.UserRequestStatus.choices())
    date = filters.DateFilter(field_name="created_time", lookup_expr="date")
    request_type = filters.CharFilter(method='filter_request_type')

    class Meta:
        model = UserRequest
        fields = [
            "status",
            "date",
            "request_type"
        ]

    def filter_request_type(self, queryset, name, value):
        mapped_value = self.REQUEST_ROLE_MAPPING.get(value)
        if mapped_value:
            return queryset.filter(request_type=mapped_value)
        return queryset
