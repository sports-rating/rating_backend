import uuid
from django_filters import rest_framework as filters

from apps.shared.utils.enums import GenderChoices, UserRoles
from apps.shared.utils.logging import logger

from apps.education.models import (
    School
)
