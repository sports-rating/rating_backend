import magic
import os

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
from apps.shared.utils.utils import CorrectPath
from apps.shared.utils.general import compress_image


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
    QUARTER_TIME = 0.25
    HALF_TIME = 0.5
    FULL_TIME = 1

    WORKLOAD_CHOICES = [
        (QUARTER_TIME, '25% (1/4 time)'),
        (HALF_TIME, '50% (1/2 time)'),
        (FULL_TIME, '100% (Full time)'),
    ]

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

    start_year = models.IntegerField(default=1800, validators=[MinValueValidator(1800)])
    start_month = models.IntegerField(choices=[(i, i) for i in range(1, 13)], default=1)
    end_year = models.IntegerField(default=1800, validators=[MinValueValidator(1800)])
    end_month = models.IntegerField(choices=[(i, i) for i in range(1, 13)], default=12)
    workload = models.FloatField(choices=WORKLOAD_CHOICES, default=FULL_TIME)


    class Meta:
        db_table = "work_place"
        verbose_name = "Work Place"
        verbose_name_plural = "Work Places"

    repr_fields = ("trainer",)

    @property
    def total_months(self):
        """Calculate total months in the period"""
        return (self.end_year - self.start_year) * 12 + (self.end_month - self.start_month) + 1


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
    request = models.OneToOneField(
        UserRequest,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="requested_result"
    )

    age_group = models.ForeignKey("federation.FederationAgeGroup", on_delete=models.SET_NULL, related_name="federation_results", blank=True, null=True)
    weight = models.CharField(max_length=10, null=True, blank=True)
    rating = models.PositiveIntegerField(default=0)
    file = models.FileField(
        upload_to=CorrectPath("media"),
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png'])],
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

    @property
    def score(self) -> float:
        return self.tournament.get_score(self.rating) if self.tournament else 0

    def save(self, *args, **kwargs):
        if self.file and hasattr(self.file, 'file'):
            mime = magic.from_buffer(self.file.read(2048), mime=True)
            self.file.seek(0)  # Reset file pointer after reading

            if mime.startswith("image/"):
                compressed_image = compress_image(self.file)
                self.file = compressed_image

            elif mime.startswith("application/pdf"):
                pass  # No compression for PDF files
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.file:
            if os.path.isfile(self.file.path):
                os.remove(self.file.path)
        super().delete(*args, **kwargs)
