from django_filters import rest_framework as filters
from django.db.models import F

from apps.shared.utils.filters import BaseFilterSet
from apps.federation.models import (
    Federation
)
from apps.user.models import UserRequest
from apps.shared.utils.enums import (
    UserRequestStatus,
    UserRequestTypes
)


class FederationFilter(BaseFilterSet):
    sport = filters.CharFilter(field_name="sports__id")

    class Meta:
        model = Federation
        fields = ["sport"]


class FederationUserRequestFilter(BaseFilterSet):
    REQUEST_ROLE_MAPPING = {
        "admin": UserRequestTypes.FEDERATION_ADMIN_REQUEST.value,
        "trainer": UserRequestTypes.TRAINER_FEDERATION_REQUEST.value
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
        return queryset.none()
