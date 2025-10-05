from django.db import models
from django.core.validators import FileExtensionValidator, MinValueValidator, MaxValueValidator

from apps.shared.models import BaseModel
from apps.user.models import (
    User,
    Trainer,
    UserRequest
)
from apps.sport.models import (
    Sport,
    SportInstitution,
    Tournament
)
from apps.shared.utils import enums


class Education(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user_educations", blank=True, null=True)
    trainer = models.ForeignKey(Trainer, on_delete=models.SET_NULL, related_name="education_records", blank=True, null=True)
    sport_institution = models.ForeignKey(SportInstitution, on_delete=models.CASCADE, related_name="educations", blank=True, null=True)
    sport = models.ForeignKey(Sport, on_delete=models.SET_NULL, related_name="sport_educations", blank=True, null=True)

    start_year = models.PositiveIntegerField(
        default=1800,
        null=True,
        validators=[
            MinValueValidator(1800)
        ]
    )
    end_year = models.PositiveIntegerField(
        default=1800,
        null=True,
        validators=[
            MinValueValidator(1800)
        ]
    )
    currently_studying = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False, help_text="Indicates whether the education has been verified by a trainer.")

    class Meta:
        db_table = "education"
        verbose_name = "Education"
        verbose_name_plural = "Educations"

    repr_fields = ("sport_institution", "start_year", "end_year")


class WorkPlace(BaseModel):
    trainer = models.ForeignKey(
        Trainer,
        on_delete=models.CASCADE,
        related_name="work_places"
    )
    sport_institution = models.ForeignKey(
        "sport.SportInstitution",
        on_delete=models.CASCADE,
        related_name="institution_trainer_work_places",
        null=True,
        blank=True
    )
    sport = models.ForeignKey(
        "sport.Sport",
        on_delete=models.SET_NULL,
        related_name="sport_trainer_work_places",
        null=True,
        blank=True
    )
    request = models.OneToOneField(
        UserRequest,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="trainer_work_place"
    )


    class Meta:
        db_table = "work_place"
        verbose_name = "Work Place"
        verbose_name_plural = "Work Places"

    repr_fields = ("trainer",)


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
    status = models.CharField(max_length=20, choices=enums.ResultVerificationStatus.choices(), default=enums.ResultVerificationStatus.PENDING.value)

    age_group = models.ForeignKey("federation.FederationAgeGroup", on_delete=models.SET_NULL, related_name="federation_results", blank=True, null=True)
    weight = models.CharField(max_length=10, null=True, blank=True)
    rating = models.PositiveIntegerField(default=0)

    gold = models.PositiveIntegerField(default=0)
    silver = models.PositiveIntegerField(default=0)
    bronze = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "result"
        ordering = ["-created_time"]

    repr_fields = ("tournament", "is_verified")

    @property
    def score(self) -> float:
        return self.tournament.get_score(self.rating) if self.tournament else 0
