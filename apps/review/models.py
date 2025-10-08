import typing as t

from django.core.validators import FileExtensionValidator, MinValueValidator, MaxValueValidator
from django.core.files.base import ContentFile
from django.utils.crypto import get_random_string
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation

from core.settings import IMAGE_DIMENSION

from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.tokens import RefreshToken


from apps.shared.models import BaseModel, BaseMedia
from apps.shared.utils.utils import CorrectPath
from apps.shared.utils import enums


class Comment(BaseModel):
    user = models.ForeignKey(
        "user.User",
        on_delete=models.CASCADE,
        related_name="user_comments",
        help_text="The user who made the comment."
    )

    sport_institution = models.ForeignKey(
        "sport.SportInstitution",
        on_delete=models.CASCADE,
        related_name="comments",
        help_text="The sport institution this comment is associated with.",
        null=True,
        blank=True
    )

    text = models.TextField()
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Rating given in the comment, must be between 1 and 5."
    )

    class Meta:
        db_table = "comment"
        verbose_name = "Comment"
        verbose_name_plural = "Comments"
        ordering = ['-created_time']

    repr_fields = ("user", "rating")

    @property
    def get_name(self):
        return f"Comment by {self.user.full_name} with rating {self.rating}"
