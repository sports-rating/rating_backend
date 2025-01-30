from django.db import models
import string 
import os

from django.db import models
from django.core.validators import FileExtensionValidator

from rest_framework.exceptions import ValidationError

from shared.models import BaseModel
from shared.addons.enums import SchoolChoices

from user.models import (
    User
)

from sport.models import (
    Sport
)


class School(BaseModel):
    name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=13)
    director = models.CharField(max_length=255, blank=True, null=True)

    address = models.JSONField() # address, district, region,...
    type = models.CharField(max_length=50, choices=SchoolChoices.choices(), default=SchoolChoices.ORDINARY.value)    
    sports = models.ManyToManyField(Sport, related_name='schools')

    class Meta:
        db_table = "school"


class Education(BaseModel):
    sport = models.ForeignKey(Sport, on_delete=models.CASCADE, related_name="educations", blank=True, null=True)
    start_year = models.DateField()
    end_year = models.DateField()
    currently_studying = models.BooleanField(default=False)
    
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="educations", blank=True, null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="educations", blank=True, null=True)

    class Meta:
        db_table = "education"
