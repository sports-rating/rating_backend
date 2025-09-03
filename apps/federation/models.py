import phonenumbers

from phonenumbers.phonenumberutil import NumberParseException

from django.db import models
from django.core.validators import FileExtensionValidator, MinValueValidator, MaxValueValidator

from rest_framework.exceptions import ValidationError

from apps.shared.models import BaseModel, Region, District, BaseMedia
from apps.shared.utils.enums import LanguageTypes, GenderChoices
from apps.shared.utils.utils import handle_file_update, handle_file_delete, CorrectPath
from apps.shared.utils.exceptions import raise_validation_error

from apps.sport.models import Sport


class Federation(BaseModel):
    name = models.CharField(max_length=250)
    is_national = models.BooleanField(default=False)
    users = models.ManyToManyField(
        "user.User",
        related_name='federations',
        help_text="Users associated with this federation",
        blank=True
    )
    parent_federation = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        related_name="child_federations",
        blank=True,
        null=True
    )
    region = models.ForeignKey(
        Region,
        on_delete=models.CASCADE,
        related_name="federations",
        null=True,
        blank=True,
    )
    sports = models.ManyToManyField(
        Sport,
        related_name="federations",
        blank=True,
        help_text="Sports associated with this federation"
    )
    address = models.TextField(null=True, blank=True)
    phone_number = models.CharField(max_length=15)
    email = models.EmailField(null=True, blank=True)
    logo = models.ImageField(
        upload_to=CorrectPath('media'),
        validators=[
            FileExtensionValidator(allowed_extensions=['heic', 'png', 'jpg', 'jpeg'])
        ],
        null=True,
        blank=True
    )
    social_media = models.JSONField(blank=True, null=True)

    class Meta:
        db_table = "federation"
        verbose_name = "Federation"
        verbose_name_plural = "Federations"
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['is_national']),
        ]

    repr_fields = ("name", "is_national")

    @property
    def get_name(self):
        return self.name

    def save(self, *args, **kwargs):
        self.clean()
        handle_file_update(self, 'logo')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        handle_file_delete(self, 'logo')
        super().delete(*args, **kwargs)

    def clean(self):
        self.check_phone_valid()

    def check_phone_valid(self):
        if self.phone_number:
            try:
                parsed_number = phonenumbers.parse(self.phone_number)
                if not phonenumbers.is_valid_number(parsed_number):
                    raise_validation_error(message="Please enter a valid phone number.")
            except NumberParseException:
                raise_validation_error(message="Please enter a valid phone number.")


class FederationDocument(BaseMedia):
    federation = models.ForeignKey(Federation, on_delete=models.CASCADE, related_name='documents')

    class Meta:
        db_table = "federation_document"
        verbose_name = "Federation Document"
        verbose_name_plural = "Federation Documents"


class AgeGroup(BaseModel):
    sport = models.ForeignKey(Sport, on_delete=models.CASCADE, related_name='age_groups')
    name = models.CharField(max_length=255)
    age = models.PositiveIntegerField(
        validators=[MinValueValidator(0)],
        default=0,
        help_text="Exact age for this age group"
    )
    weights = models.JSONField(
        default=list,
        help_text="List of allowed weights for this age group"
    )
    gender = models.CharField(
        max_length=20,
        choices=GenderChoices.choices(),
        default=GenderChoices.MALE.value,
    )

    class Meta:
        db_table = "age_group"
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['gender'])
        ]
        verbose_name = "Age Group"
        verbose_name_plural = "Age Groups"

    repr_fields = ("name", "age", "sport")


class FederationAgeGroup(BaseModel):
    age_group = models.ForeignKey(AgeGroup, on_delete=models.CASCADE, related_name='federation_links')
    federation = models.ForeignKey(Federation, on_delete=models.CASCADE, related_name='age_group_links')
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "federation_age_group"
        indexes = [
            models.Index(fields=['is_active']),
        ]
        verbose_name = "Federation Age Group"
        verbose_name_plural = "Federation Age Groups"

    repr_fields = ("age_group", "federation")
