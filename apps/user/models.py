import random
import string
import os
import mimetypes
import io
import phonenumbers

from PIL import Image
from faker import Faker
from tabnanny import verbose
from phonenumbers.phonenumberutil import NumberParseException

from django.core.validators import FileExtensionValidator
from django.core.files.base import ContentFile
from django.utils.crypto import get_random_string
from django.db import models
from django.contrib.auth.models import AbstractUser
from core.settings import IMAGE_DIMENSION

from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.tokens import RefreshToken

from apps.shared.models import BaseModel, BaseMedia
from apps.shared.utils.utils import CorrectPath
from apps.shared.utils import enums

from apps.sport.models import (
    Sport,
)
from apps.federation.models import (
    Federation
)

fake = Faker()


class User(AbstractUser, BaseModel):
    first_name = models.CharField(max_length=100, null=True, blank=True)
    middle_name = models.CharField(max_length=100, null=True, blank=True)
    last_name = models.CharField(max_length=100, null=True, blank=True)

    pinfl = models.CharField(
        max_length=14,
        blank=True,
        null=True
    )
    region = models.ForeignKey("shared.Region", on_delete=models.SET_NULL, related_name="users", null=True, blank=True)
    district = models.ForeignKey("shared.District", on_delete=models.SET_NULL, related_name="users", null=True, blank=True)
    gender = models.CharField(max_length=30, choices=enums.GenderChoices.choices(), default=enums.GenderChoices.MALE.value, null=True, blank=True)
    user_role = models.CharField(max_length=50, choices=enums.UserRoles.choices(), default=enums.UserRoles.ORDINARY.value)
    phone_number = models.CharField(max_length=13, null=True, blank=True)
    email = models.CharField(null=True, blank=True)

    birth_date = models.DateField(null=True, blank=True)
    is_verified = models.BooleanField(default=False)

    class Meta:
        db_table = "user"
        ordering = ["-created_time"]

    @property
    def full_name(self):
        return f"{self.last_name} {self.first_name} {self.middle_name}"

    @property
    def federation(self):
        return self.federations.first()

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if hasattr(self, 'sportsman_profile'):
            self.sportsman_profile.delete() # triggers delete method in Sportsman
        elif hasattr(self, 'trainer_profile'):
            self.trainer_profile.delete() # triggers delete method in Trainer
        super().delete(*args, **kwargs)

    def clean(self):
        self.check_username()
        self.check_phone_valid()
        self.check_pinfl()

    def check_phone_valid(self):
        if self.phone_number:
            try:
                parsed_number = phonenumbers.parse(self.phone_number)
                if not phonenumbers.is_valid_number(parsed_number):
                    raise ValidationError("Please enter a valid phone number.")
            except NumberParseException:
                raise ValidationError("Please enter a valid phone number.")

    def check_pinfl(self):
        if self.pinfl and not self.pinfl.isdigit():
            raise ValidationError("PINFL must contain only numbers.")

    def check_username(self):
        print(f"checking username for {self.username}")
        if not self.username:
            if self.first_name and self.last_name and self.phone_number:
                base_username = f"{self.first_name.lower()}_{self.last_name.lower()}_{self.phone_number[-4:]}"
            else:
                base_username = fake.user_name()

            username = base_username
            while User.objects.filter(username=username).exists():
                username = f"{base_username}_{get_random_string(4)}"

            self.username = username

    def tokens(self) -> dict[str, str]:
        refresh = RefreshToken.for_user(self)
        return dict(
            access=str(refresh.access_token),
            refresh=str(refresh),
        )


class Sportsman(models.Model):
    user = models.OneToOneField(User, primary_key=True, on_delete=models.CASCADE, related_name='sportsman_profile')
    sport = models.ForeignKey(Sport, on_delete=models.CASCADE, related_name="sportsmen", blank=True, null=True) # will likely changes
    trainer = models.ForeignKey("user.Trainer", on_delete=models.CASCADE, related_name="sportsmen", blank=True, null=True)

    bio = models.TextField(blank=True, null=True)
    division = models.CharField(max_length=100, blank=True, null=True)
    sport_rank = models.CharField(max_length=30, choices=enums.SportRankEnum.choices(), default=enums.SportRankEnum.YOUTH_3.value, blank=True, null=True)
    user_metrics = models.JSONField(blank=True, null=True)
    # Address
    address = models.JSONField(blank=True, null=True)
    # Contacts
    social_media = models.JSONField(blank=True, null=True)
    is_sportsman_verified = models.BooleanField(default=False)

    created_time = models.DateTimeField(auto_now_add=True, null=True)
    updated_time = models.DateTimeField(auto_now=True, null=True)


    class Meta:
        db_table = "sportsman"
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['sport']),
            models.Index(fields=['trainer']),
            models.Index(fields=['is_sportsman_verified'])
        ]
        verbose_name = "Sportsman Profile"
        verbose_name_plural = "Sportsmen Profiles"

    def __str__(self):
        return f"Sportsman {self.user.first_name} - {self.user.last_name}"


class Trainer(models.Model):
    user = models.OneToOneField(User, primary_key=True, on_delete=models.CASCADE, related_name='trainer_profile')
    sport = models.ForeignKey(Sport, on_delete=models.CASCADE, related_name="trainers", blank=True, null=True)
    federation = models.ForeignKey("federation.Federation", on_delete=models.CASCADE, related_name="trainers", blank=True, null=True)

    skill_level = models.CharField(max_length=100, null=True, blank=True)
    bio = models.TextField(blank=True, null=True)
    division = models.CharField(max_length=100, blank=True, null=True)
    user_metrics = models.JSONField(blank=True, null=True)
    # Address
    address = models.JSONField(blank=True, null=True)
    # Contacts
    social_media = models.JSONField(blank=True, null=True)
    is_trainer_verified = models.BooleanField(default=False)

    created_time = models.DateTimeField(auto_now_add=True, null=True)
    updated_time = models.DateTimeField(auto_now=True, null=True)


    # General Results
    # number_of_games = models.PositiveIntegerField(blank=True, null=True)
    # number_of_students = models.PositiveIntegerField(blank=True, null=True)
    # number_of_awards = models.PositiveIntegerField(blank=True, null=True)

    class Meta:
        db_table = "trainer"
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['sport']),
            models.Index(fields=['is_trainer_verified'])
        ]
        verbose_name = "Trainer Profile"
        verbose_name_plural = "Trainers Profiles"

    def __str__(self):
        return f"Trainer {self.user.first_name} - {self.user.last_name}"


class ArchivedTrainer(models.Model):
    name = models.CharField(max_length=255)


class UserMedia(BaseMedia):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='media', blank=True, null=True)
    is_profile_photo = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if self.is_profile_photo:
            # Ensure only one profile photo per user
            UserMedia.objects.filter(user=self.user, is_profile_photo=True).update(is_profile_photo=False)
        super().save(*args, **kwargs)


class UserRequest(BaseModel):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_requests')
    # receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_requests')
    receivers = models.ManyToManyField(
        User,
        related_name='received_requests',
        help_text="Users who will receive this request",
    )
    federation = models.ForeignKey(
        Federation,
        on_delete=models.CASCADE,
        related_name='requests',
        null=True, blank=True,
        help_text="The federation this request is related to"
    )

    request_type = models.CharField(max_length=100, choices=enums.UserRequestTypes.choices(), default=enums.UserRequestTypes.TRAINER_REQUEST.value)
    status = models.CharField(max_length=50, choices=enums.UserRequestStatus.choices(), default=enums.UserRequestStatus.PENDING.value)

    message = models.TextField(null=True, blank=True)
    data = models.JSONField(null=True, blank=True) # for future extensibility

    class Meta:
        db_table = "user_request"
        indexes = [
            models.Index(fields=['sender']),
            models.Index(fields=['request_type']),
            models.Index(fields=['status'])
        ]
        verbose_name = "User Request"
        verbose_name_plural = "User Requests"

    def __str__(self):
        return f"{self.sender.username} -> {self.receivers.all().values_list('username', flat=True)} ({self.request_type}) - {self.status}"


class UserNotification(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255, null=True, blank=True)
    text=models.TextField()
    is_read = models.BooleanField(default=False)
    request = models.ForeignKey(UserRequest, on_delete=models.CASCADE, related_name='notifications', null=True, blank=True)
    data = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = "user_notification"
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['title']),
            models.Index(fields=['is_read']),
        ]
        verbose_name = "User Notification"
        verbose_name_plural = "User Notifications"

    def __str__(self):
        return f"Notification for {self.user.username}: {self.title or 'No Title'} - {'Read' if self.is_read else 'Unread'}"
