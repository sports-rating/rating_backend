from django_filters import rest_framework as filters
from django.db.models import F, Q

from apps.shared.utils.filters import BaseFilterSet
from apps.federation.models import (
    Federation
)
from apps.user.models import (
    UserRequest,
    User
)
from apps.shared.utils.enums import (
    UserRequestStatus,
    UserRequestTypes,
    UserRoles,
    GenderChoices
)


class FederationFilter(BaseFilterSet):
    sport = filters.CharFilter(field_name="sports__id")

    class Meta:
        model = Federation
        fields = ["sport"]


class FederationUsersFilter(BaseFilterSet):
    user_role = filters.ChoiceFilter(choices=UserRoles.choices())
    sport = filters.CharFilter(method="filter_sport")
    region = filters.CharFilter(field_name='region__id')
    district = filters.CharFilter(field_name='district__id')
    gender = filters.ChoiceFilter(choices=GenderChoices.choices())

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


class FederationUserRequestFilter(BaseFilterSet):
    # TODO: CoderB7:
    # Change the mapping to use "federation_admin" instead of "admin"
    REQUEST_ROLE_MAPPING = {
        "admin": UserRequestTypes.FEDERATION_ADMIN_REQUEST.value, # change to federation_admin
        "trainer": UserRequestTypes.TRAINER_FEDERATION_REQUEST.value,
        "trainer_workplace_verification": UserRequestTypes.TRAINER_WORKPLACE_VERIFICATION_REQUEST.value,
    }

    status = filters.ChoiceFilter(choices=UserRequestStatus.choices())
    date = filters.DateFilter(field_name="created_time", lookup_expr="date")
    type = filters.CharFilter(method='filter_type')

    class Meta:
        model = UserRequest
        fields = [
            "status",
            "date",
            "type"
        ]

    def filter_type(self, queryset, name, value):
        mapped_value = self.REQUEST_ROLE_MAPPING.get(value)
        print(mapped_value)
        if mapped_value:
            return queryset.filter(request_type=mapped_value)
        return queryset
