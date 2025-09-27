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


class Education(BaseModel):
    sport = models.ForeignKey(Sport, on_delete=models.CASCADE, related_name="educations", blank=True, null=True)
    # TODO:CoderB7 remove start_year and end_year
    start_year = models.DateField()
    end_year = models.DateField()
    currently_studying = models.BooleanField(default=False)

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="educations", blank=True, null=True)
    # trainer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="trainer_educations", blank=True, null=True) # ?
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="educations", blank=True, null=True)

    class Meta:
        db_table = "education"

    repr_fields = ("school", "start_year", "end_year")
