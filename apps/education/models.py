import string
import os

from django.db import models
from django.core.validators import FileExtensionValidator

from rest_framework.exceptions import ValidationError

from apps.shared.utils.enums import SchoolChoices

from apps.shared.models import BaseModel
from apps.user.models import (
    User
)
from apps.sport.models import (
    Sport,
    School
)
