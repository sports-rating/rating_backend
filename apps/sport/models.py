import string
import os

from django.db import models
from django.core.validators import FileExtensionValidator, MinValueValidator, MaxValueValidator

from rest_framework.exceptions import ValidationError

from apps.shared.models import BaseModel, Region, District, BaseMedia
from apps.shared.utils.enums import (
    LanguageTypes,
    GenderChoices,
    ResultVerificationStatus
)
from apps.shared.utils.utils import (
    handle_file_update,
    handle_file_delete,
    CorrectPath
)


class Sport(BaseModel):
    name = models.CharField(max_length=250)
    logo = models.ImageField(
        upload_to=CorrectPath('media'),
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

    repr_fields = ("name",)

    @property
    def get_name(self):
        return self.name

    def save(self, *args, **kwargs):
        handle_file_update(self, 'logo')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        handle_file_delete(self, 'logo')
        super().delete(*args, **kwargs)


class Tournament(BaseModel):
    name = models.CharField(max_length=450)
    sport = models.ForeignKey(Sport, on_delete=models.CASCADE, related_name="tournaments", blank=True, null=True)
    logo = models.ImageField(
        upload_to=CorrectPath('media'),
        validators=[
            FileExtensionValidator(allowed_extensions=['heic', 'png', 'jpg', 'jpeg'])
        ],
        null=True,
        blank=True
    )
    federation = models.ForeignKey(
        "federation.Federation",
        on_delete=models.CASCADE,
        related_name="tournaments",
        blank=True,
        null=True
    )

    class Meta:
        db_table = "tournament"
        verbose_name = "Tournament"
        verbose_name_plural = "Tournaments"

    repr_fields = ("name", "federation")

    @property
    def get_name(self):
        return self.name

    def get_score(self, position):
        scoring_policy: ScoringPolicy = self.scoring_policies.filter(position=position).first()
        return scoring_policy.score if scoring_policy else 0

    def save(self, *args, **kwargs):
        handle_file_update(self, 'logo')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        handle_file_delete(self, 'logo')
        super().delete(*args, **kwargs)


class ScoringPolicy(BaseModel):
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name="scoring_policies")
    position = models.PositiveIntegerField()
    score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[
            MinValueValidator(0),
        ]
    )

    class Meta:
        db_table = "scoring_policy"
        unique_together = ['tournament', 'position']
        verbose_name = "Scoring Policy"
        verbose_name_plural = "Scoring Policies"
        ordering = ["position"]

    repr_fields = ("tournament", "position", "score")


class Result(BaseModel):
    country = models.CharField(max_length=100, null=True, blank=True)
    year = models.PositiveIntegerField(
        default=1800,
        null=True,
        validators=[
            MinValueValidator(1800)
        ]
    )
    currently_participating = models.BooleanField(default=False)

    user = models.ForeignKey("user.User", on_delete=models.CASCADE, related_name="results", blank=True, null=True)
    trainer = models.ForeignKey("user.Trainer", on_delete=models.SET_NULL, related_name='assisted_results', blank=True, null=True)
    archived_trainer = models.ForeignKey("user.ArchivedTrainer", on_delete=models.SET_NULL, related_name='archived_assisted_results', blank=True, null=True)

    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name="tournament_results", blank=True, null=True)
    additional_attributes = models.JSONField(null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=ResultVerificationStatus.choices(), default=ResultVerificationStatus.PENDING.value)

    rating = models.PositiveIntegerField(default=0)
    score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[
            MinValueValidator(0),
        ],
        null=True,
        blank=True
    )

    gold = models.PositiveIntegerField(default=0)
    silver = models.PositiveIntegerField(default=0)
    bronze = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "result"
        ordering = ["-created_time"]

    repr_fields = ("tournament", "is_verified")


class Team(BaseModel):
    name = models.CharField(max_length=250, unique=True)
    sport = models.ForeignKey(Sport, on_delete=models.CASCADE, related_name='teams')

    founded_year = models.IntegerField(blank=True, null=True)
    logo = models.ImageField(
        upload_to=CorrectPath('media'),
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

    class Meta:
        db_table = "team"

    repr_fields = ("name", "sport")

    def save(self, *args, **kwargs):
        handle_file_update(self, 'logo')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        handle_file_delete(self, 'logo')
        super().delete(*args, **kwargs)
