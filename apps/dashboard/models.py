from django.db import models
import string 
import os

from django.db import models

from rest_framework.exceptions import ValidationError
from shared.models import BaseModel
from shared.addons.utils import CorrectPath


class Tournament(BaseModel):
    name = models.CharField(max_length=450)
    start_time = models.DateField()
    end_time = models.DateField()
    place = models.CharField(max_length=450)
    division = models.CharField(max_length=100)
    sport_type = models.CharField(max_length=100)

    class Meta:
        db_table = "tournament"
    
    def __str__(self):
        return self.name
    

