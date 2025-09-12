import string
import os

from django.db import models
from django.core.validators import FileExtensionValidator

from rest_framework.exceptions import ValidationError

from apps.shared.models import BaseModel
from apps.shared.utils import enums


class PrivacyPolicy(BaseModel):
    title = models.CharField(max_length=255)
    language = models.CharField(
        max_length=15, choices=enums.LanguageTypes.choices(), default=enums.LanguageTypes.EN.value
    )
    text = models.TextField()

    def __str__(self):
        return self.title

    class Meta:
        db_table = "privacy_policy"
        verbose_name = "Privacy Policy"
        verbose_name_plural = "Privacy Policies"


class TermsOfCondition(BaseModel):
    title = models.CharField(max_length=255)
    language = models.CharField(
        max_length=15, choices=enums.LanguageTypes.choices(), default=enums.LanguageTypes.EN.value
    )
    text = models.TextField()

    def __str__(self):
        return self.title

    class Meta:
        db_table = "terms_of_condition"
        verbose_name = "Terms of Condition"
        verbose_name_plural = "Terms of Conditions"
