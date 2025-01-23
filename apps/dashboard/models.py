from django.db import models
import string 
import os

from django.db import models

from rest_framework.exceptions import ValidationError
from shared.models import BaseModel
from shared.addons.enums import LanguageTypes


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
    # end_time = models.DateField() # will be removed
    place = models.CharField(max_length=450)
    division = models.CharField(max_length=100) # razdeleniya?
    sport = models.ForeignKey(Sport, on_delete=models.CASCADE, related_name="tournaments", blank=True, null=True)
    logo = models.ManyToManyField("user.Media", related_name='tournament_logo', blank=True)

    class Meta:
        db_table = "tournament"
    
    def __str__(self):
        return self.name


class Team(BaseModel):
    name = models.CharField(max_length=250, unique=True)
    sport = models.ForeignKey(Sport, on_delete=models.CASCADE, related_name='teams')

    founded_year = models.IntegerField(blank=True, null=True)
    logo = models.ManyToManyField('user.Media', related_name='team_logos', blank=True)

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


class PrivacyPolicy(BaseModel):
    title = models.CharField(max_length=255)
    language = models.CharField(
        max_length=15, choices=LanguageTypes.choices(), default=LanguageTypes.EN.value
    )
    text = models.TextField()

    def __str__(self):
        return self.title

    class Meta:
        db_table = "privacy_policy"
        verbose_name = "Privacy Policy"
        verbose_name_plural = "Privacy Policy"


class TermsOfCondition(BaseModel):
    title = models.CharField(max_length=255)
    language = models.CharField(
        max_length=15, choices=LanguageTypes.choices(), default=LanguageTypes.EN.value
    )
    text = models.TextField()

    def __str__(self):
        return self.title

    class Meta:
        db_table = "terms_of_condition"
        verbose_name = "Terms of Condition"
        verbose_name_plural = "Terms of Conditions"

