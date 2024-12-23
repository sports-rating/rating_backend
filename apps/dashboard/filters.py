import uuid
from django_filters import rest_framework as filters

from shared.addons.enums import SportsType, GenderChoices, UserRoles
from user.models import (
    Sportsman,
    Trainer,
    User
)

class UserFilter(filters.FilterSet):
    user_role = filters.CharFilter()

    class Meta:
        model = User
        fields = ["user_role"]
    
    def filter_user_role(self, queryset, name, value):  # noqa
        if value == "sportsman":
            return queryset.filter(sportsman_profile__isnull=False)
        elif value == "trainer":
            return queryset.filter(trainer_profile__isnull=False)
        elif value == "ordinary":
            return queryset.filter(sportsman_profile__isnull=True, trainer_profile__isnull=True)
        return queryset