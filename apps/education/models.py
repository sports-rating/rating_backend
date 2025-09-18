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
    Sport
)


class School(BaseModel):
    name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=13)
    director = models.CharField(max_length=255, blank=True, null=True)
    type = models.CharField(max_length=50, choices=SchoolChoices.choices(), default=SchoolChoices.ORDINARY.value)

    address = models.TextField(null=True, blank=True)
    latitude = models.FloatField(default="0.0")
    longitude = models.FloatField(default="0.0")
    region = models.ForeignKey(
        "shared.Region",
        on_delete=models.SET_NULL,
        related_name="region_schools",
        null=True,
        blank=True
    )
    district = models.ForeignKey(
        "shared.District",
        on_delete=models.SET_NULL,
        related_name="district_schools",
        null=True,
        blank=True
    )

    sports = models.ManyToManyField(Sport, related_name='schools')

    class Meta:
        db_table = "school"
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["phone_number"])
        ]
        verbose_name = "School"
        verbose_name_plural = "Schools"

    repr_fields = ("name",)


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
