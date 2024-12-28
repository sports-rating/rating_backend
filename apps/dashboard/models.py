from django.db import models
import string 
import os

from django.db import models

from rest_framework.exceptions import ValidationError
from shared.models import BaseModel
from shared.addons.utils import CorrectPath



class Sport(BaseModel):
    name = models.CharField(max_length=250)
    logo = models.ManyToManyField("user.Media", related_name='sport_logo', blank=True)

    class Meta:
        db_table = "sport"
    
    def __str__(self):
        return self.name


class Tournament(BaseModel):
    name = models.CharField(max_length=450)
    start_time = models.DateField()
    end_time = models.DateField()
    place = models.CharField(max_length=450)
    division = models.CharField(max_length=100)
    sport = models.ForeignKey(Sport, models.CASCADE, related_name="tournaments", blank=True, null=True)
    logo = models.ManyToManyField("user.Media", related_name='tournament_logo', blank=True)

    class Meta:
        db_table = "tournament"
    
    def __str__(self):
        return self.name




