from django.db import models
import string 
import os

from django.db import models
from django.core.validators import FileExtensionValidator

from rest_framework.exceptions import ValidationError

from shared.models import BaseModel
from shared.addons.enums import LanguageTypes
from shared.addons.utils import handle_file_update, handle_file_delete

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
    
    def save(self, *args, **kwargs):
        handle_file_update(self, 'logo')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        handle_file_delete(self, 'logo')
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
    
    def save(self, *args, **kwargs):
        handle_file_update(self, 'logo')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        handle_file_delete(self, 'logo')
        super().delete(*args, **kwargs)


class Result(BaseModel):
    country = models.CharField(max_length=100)
    year = models.DateField(blank=True, null=True)
    currently_participating = models.BooleanField(default=False)
    
    user = models.ForeignKey("user.User", on_delete=models.CASCADE, related_name="results", blank=True, null=True)
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name="results", blank=True, null=True)
    additional_attributes = models.JSONField(null=True, blank=True)

    rating = models.IntegerField(null=True, blank=True)
    number_of_gold = models.PositiveIntegerField(blank=True, null=True)
    number_of_silver = models.PositiveIntegerField(blank=True, null=True)
    number_of_bronze = models.PositiveIntegerField(blank=True, null=True)

    class Meta: 
        db_table = "result"
    
    def __str__(self):
        return f"{self.tournament.name} - {self.year}"
    

class Team(BaseModel):
    name = models.CharField(max_length=250, unique=True)
    sport = models.ForeignKey(Sport, on_delete=models.CASCADE, related_name='teams')

    founded_year = models.IntegerField(blank=True, null=True)
    logo = models.ImageField(
        upload_to='team/logos', 
        validators=[
            FileExtensionValidator(allowed_extensions=['heic', 'png', 'jpg', 'jpeg'])
        ],
        null=True, 
        blank=True                         
    )

    members = models.ManyToManyField(
        "user.User",
        related_name='teams',
        blank=True
    )

    social_media = models.JSONField(blank=True)

    # Statistics
    wins = models.PositiveIntegerField(default=0, blank=True, null=True)
    losses = models.PositiveIntegerField(default=0, blank=True, null=True)
    draws = models.PositiveIntegerField(default=0, blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "team"