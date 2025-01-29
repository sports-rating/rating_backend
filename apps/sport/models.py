from django.db import models
import string 
import os

from django.db import models
from django.core.validators import FileExtensionValidator

from rest_framework.exceptions import ValidationError

from user.models import User
from shared.models import BaseModel
from shared.addons.enums import LanguageTypes


class Sport(BaseModel):
    name = models.CharField(max_length=250)
    logo = models.ImageField(
        upload_to='sport/logos', 
        validators=[
            FileExtensionValidator(allowed_extensions=['heic', 'png', 'jpg', 'jpeg'])
        ],
        null=True, 
        blank=True                         
    )

    class Meta:
        db_table = "sport"
        verbose_name = "Sport"
        verbose_name_plural = "Sports"
    
    def __str__(self):
        return self.name
    
    def delete(self, *args, **kwargs):
        if self.logo:
            if os.path.isfile(self.logo.path):
                os.remove(self.logo.path)
        super().delete(*args, **kwargs)


class Tournament(BaseModel):
    name = models.CharField(max_length=450)
    start_time = models.DateField()
    place = models.CharField(max_length=450)
    division = models.CharField(max_length=100) # razdeleniya?
    sport = models.ForeignKey(Sport, on_delete=models.CASCADE, related_name="tournaments", blank=True, null=True)
    logo = models.ImageField(
        upload_to='tournament/logos', 
        validators=[
            FileExtensionValidator(allowed_extensions=['heic', 'png', 'jpg', 'jpeg'])
        ],
        null=True, 
        blank=True                         
    )

    class Meta:
        db_table = "tournament"
        verbose_name = "Tournament"
        verbose_name_plural = "Tournaments"
    
    def __str__(self):
        return self.name
    
    def delete(self, *args, **kwargs):
        if self.logo:
            if os.path.isfile(self.logo.path):
                os.remove(self.logo.path)
        super().delete(*args, **kwargs)


class Result(BaseModel):
    country = models.CharField(max_length=100)
    year = models.DateField(blank=True, null=True)
    currently_participating = models.BooleanField(default=False)
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="results", blank=True, null=True)
    tournament = models.ForeignKey("dashboard.Tournament", on_delete=models.CASCADE, related_name="results", blank=True, null=True)
    additional_attributes = models.JSONField(null=True, blank=True)

    rating = models.IntegerField(null=True, blank=True)
    number_of_gold = models.PositiveIntegerField(blank=True, null=True)
    number_of_silver = models.PositiveIntegerField(blank=True, null=True)
    number_of_bronze = models.PositiveIntegerField(blank=True, null=True)

    class Meta: 
        db_table = "result"