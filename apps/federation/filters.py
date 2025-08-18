from django_filters import rest_framework as filters
from django.db.models import F

from apps.shared.utils.filters import BaseFilterSet
from apps.federation.models import (
    Federation
)
from apps.user.models import UserRequest
from apps.shared.utils.enums import UserRequestStatus
