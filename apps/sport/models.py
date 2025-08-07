import string 
import os

from django.db import models
from django.core.validators import FileExtensionValidator, MinValueValidator, MaxValueValidator

from rest_framework.exceptions import ValidationError

from apps.shared.models import BaseModel, Region, District
from apps.shared.utils.enums import LanguageTypes, GenderChoices
from apps.shared.utils.utils import handle_file_update, handle_file_delete, CorrectPath


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
    sport = models.ForeignKey(Sport, on_delete=models.CASCADE, related_name="tournaments", blank=True, null=True)
    logo = models.ImageField(
        upload_to=CorrectPath('media'), 
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

    rating = models.PositiveIntegerField(default=0)
    gold = models.PositiveIntegerField(default=0)
    silver = models.PositiveIntegerField(default=0)
    bronze = models.PositiveIntegerField(default=0)

    class Meta: 
        db_table = "result"
    
    def __str__(self):
        return f"{self.tournament.name} - {self.year}"


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

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        handle_file_update(self, 'logo')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        handle_file_delete(self, 'logo')
        super().delete(*args, **kwargs)

    class Meta:
        db_table = "team"


class Federation(BaseModel):
    name = models.CharField(max_length=250)
    is_national = models.BooleanField(default=False)
    users = models.ManyToManyField(
        "user.User",
        related_name='federations',
        help_text="Users associated with this federation",
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
    )
    sports = models.ManyToManyField(
        Sport,
        related_name="federations",
        blank=True,
        help_text="Sports associated with this federation"
    )
    address = models.TextField(null=True, blank=True)
    phone_number = models.CharField(max_length=15, unique=True)
    email = models.EmailField(null=True, blank=True)
    logo = models.ImageField(
        upload_to=CorrectPath('media'), 
        validators=[
            FileExtensionValidator(allowed_extensions=['heic', 'png', 'jpg', 'jpeg'])
        ],
        null=True, 
        blank=True                         
    )
    website = models.URLField(null=True, blank=True)
    document = models.FileField(
        upload_to=CorrectPath('media'),
        validators=[
            FileExtensionValidator(allowed_extensions=['pdf', 'docx', 'txt'])
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
            models.Index(fields=['region']),
            models.Index(fields=['is_national']),
        ]

    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        handle_file_update(self, 'logo')
        handle_file_update(self, 'document')
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        handle_file_delete(self, 'logo')
        handle_file_delete(self, 'document')
        super().delete(*args, **kwargs)


class AgeGroup(BaseModel):
    sport = models.ForeignKey(Sport, on_delete=models.CASCADE, related_name='age_groups')
    federation = models.ForeignKey(Federation, on_delete=models.CASCADE, related_name='age_groups', blank=True, null=True)
    name = models.CharField(max_length=255)
    min_age = models.PositiveIntegerField(
        validators=[MinValueValidator(0)],
        help_text="Minimum age for this age group"
    )
    max_age = models.PositiveIntegerField(
        validators=[MinValueValidator(0)],
        help_text="Maximum age for this age group"
    )
    gender = models.CharField(
        max_length=20,
        choices=GenderChoices.choices(),
        default=GenderChoices.MALE.value,
    )

    class Meta:
        db_table = "age_group"
        indexes = [
            models.Index(fields=['sport']),
            models.Index(fields=['federation']),
            models.Index(fields=['name']),
            models.Index(fields=['gender'])
        ]
        verbose_name = "Age Group"
        verbose_name_plural = "Age Groups"

    def __str__(self):
        return f"{self.name} ({self.min_age}-{self.max_age}) - {self.sport.name}"


class WeightCategoryType(BaseModel):
    name = models.CharField(max_length=255)

    class Meta:
        db_table = "weight_category_type"
        verbose_name = "Weight Category Type"
        verbose_name_plural = "Weight Category Types"

    def __str__(self):
        return self.name


class WeightCategory(BaseModel):
    type = models.ForeignKey(WeightCategoryType, on_delete=models.CASCADE, related_name='weight_categories')
    age_group = models.ForeignKey(AgeGroup, on_delete=models.CASCADE, related_name='weight_categories')
    min_weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Minimum weight for this category"
    )
    max_weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Maximum weight for this category"
    )

    class Meta:
        db_table = "weight_category"
        indexes = [
            models.Index(fields=['age_group']),
        ]
        unique_together = [('age_group', 'min_weight', 'max_weight')]
        verbose_name = "Weight Category"
        verbose_name_plural = "Weight Categories"

    def __str__(self):
        return f"{self.age_group.name} - {self.min_weight}kg to {self.max_weight}kg"
