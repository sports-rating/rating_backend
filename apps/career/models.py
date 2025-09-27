from django.db import models

from apps.shared.models import BaseModel
from apps.user.models import (
    User,
    Trainer,
    UserRequest
)
from apps.sport.models import (
    Sport,
    School
)


class Education(BaseModel):
    sport = models.ForeignKey(Sport, on_delete=models.CASCADE, related_name="educations", blank=True, null=True)
    # TODO:CoderB7 remove start_year and end_year
    start_year = models.DateField()
    end_year = models.DateField()
    currently_studying = models.BooleanField(default=False)

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="educations", blank=True, null=True)
    # trainer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="trainer_educations", blank=True, null=True) # ?
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="educations", blank=True, null=True)

    class Meta:
        db_table = "education"

    repr_fields = ("school", "start_year", "end_year")


class WorkPlace(BaseModel):
    trainer = models.ForeignKey(
        Trainer,
        on_delete=models.CASCADE,
        related_name="work_places"
    )
    school = models.ForeignKey(
        "sport.School",
        on_delete=models.CASCADE,
        related_name="school_trainer_work_places",
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
