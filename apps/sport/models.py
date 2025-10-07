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
from apps.shared.utils import enums


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


class SportInstitution(BaseModel):
    user = models.ForeignKey(
        "user.User",
        on_delete=models.CASCADE,
        related_name="sport_institutions",
        null=True,
        blank=True
    )
    name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=13)
    director = models.CharField(max_length=255, blank=True, null=True)
    type = models.CharField(max_length=50, choices=enums.SportInstitutionChoices.choices(), default=enums.SportInstitutionChoices.SPORT_SCHOOL.value)
    work_time = models.CharField(max_length=100, null=True, blank=True)

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

    sports = models.ManyToManyField(Sport, related_name='institutions')

    class Meta:
        db_table = "sport_institution"
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["phone_number"])
        ]
        verbose_name = "Sport Institution"
        verbose_name_plural = "Sport Institutions"

    repr_fields = ("name",)


class SportInstitutionMedia(BaseMedia):
    sport_institution = models.ForeignKey(
        SportInstitution,
        on_delete=models.CASCADE,
        related_name='media',
        blank=True,
        null=True
    )

    class Meta:
        db_table = "sport_institution_media"
        verbose_name = "Sport Institution Media"
        verbose_name_plural = "Sport Institution Media"

    def save(self, *args, **kwargs):
        return super().save(*args, **kwargs)


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


class SportInstitutionRequest(BaseModel):

    # User who sent the request
    manager_first_name = models.CharField(max_length=255)
    manager_last_name = models.CharField(max_length=255)
    manager_phone_number = models.CharField(max_length=13)

    # Sport Institution details
    school_name = models.CharField(max_length=255)
    school_phone_number = models.CharField(max_length=13)
    school_director = models.CharField(max_length=255, blank=True, null=True)
    school_type = models.CharField(max_length=50, choices=enums.SportInstitutionChoices.choices(), default=enums.SportInstitutionChoices.SPORT_SCHOOL.value)
    school_address = models.TextField(null=True, blank=True)
    school_latitude = models.FloatField(default="0.0")
    school_longitude = models.FloatField(default="0.0")
    school_region = models.CharField(max_length=100)
    school_district = models.CharField(max_length=100)
    school_sports = models.JSONField(default=list)

    processed_by = models.ForeignKey(
        "user.User",
        on_delete=models.SET_NULL,
        related_name="processed_sport_institution_requests",
        null=True,
        blank=True
    )
    processed_time = models.DateTimeField(null=True, blank=True, help_text="Time when the request was processed")

    additional_info = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=50, choices=enums.SportInstitutionRequestStatus.choices(), default=enums.SportInstitutionRequestStatus.PENDING.value)

    class Meta:
        db_table = "sport_institution_request"
        indexes = [
            models.Index(fields=["manager_phone_number"]),
            models.Index(fields=["school_name"]),
            models.Index(fields=["status"]),
        ]
        verbose_name = "Sport Institution Request"
        verbose_name_plural = "Sport Institution Requests"

    repr_fields = ("manager_phone_number", "school_name", "status")
