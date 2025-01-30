import random
import string
import os
import mimetypes
import io

import phonenumbers
from PIL import Image
from django.core.validators import FileExtensionValidator
from django.core.files.base import ContentFile

from django.db import models
from django.contrib.auth.models import AbstractUser

from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.tokens import RefreshToken

from phonenumbers.phonenumberutil import NumberParseException
from shared.models import BaseModel, BaseMedia
from shared.addons.enums import GenderChoices, MediaChoices, UserRoles, SchoolChoices
from core.settings import IMAGE_DIMENSION
from shared.addons.utils import CorrectPath

from sport.models import (
    Sport
)


class User(AbstractUser, BaseModel):
    first_name = models.CharField(max_length=100, null=True, blank=True)
    middle_name = models.CharField(max_length=100, null=True, blank=True)
    last_name = models.CharField(max_length=100, null=True, blank=True)
    
    pinfl = models.CharField(
        max_length=14,
        blank=True, 
        null=True
    )
    gender = models.CharField(max_length=30, choices=GenderChoices.choices(), default=GenderChoices.MALE.value, null=True, blank=True)
    user_role = models.CharField(max_length=50, choices=UserRoles.choices(), default=UserRoles.ORDINARY.value)
    phone_number = models.CharField(max_length=13, null=True, blank=True)
    email = models.CharField(null=True, blank=True)
    
    birth_date = models.DateField(null=True, blank=True)
    is_verified = models.BooleanField(default=False)

    class Meta:
        db_table = "user"
        ordering = ["-created_time"]

    def __str__(self):
        return f"{self.first_name} {self.last_name}"
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
       
    def delete(self, *args, **kwargs):
        # media_objects = self.photo.all()

        # for media in media_objects:
        #     media.delete()

        if hasattr(self, 'sportsman_profile'):
            self.sportsman_profile.delete() # triggers delete method in Sportsman
        elif hasattr(self, 'trainer_profile'):
            self.trainer_profile.delete() # triggers delete method in Trainer
        super().delete(*args, **kwargs)

    @property
    def full_name(self):
        return f"{self.last_name} {self.first_name} {self.middle_name}"

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

    def clean(self):
        self.check_username()
        self.check_phone_valid()
        self.check_pinfl()
    
    def check_username(self):
        print(f"checking username for {self.username}")
        if not self.username:
            # Generate a fake username using random strings and phone number
            random_str = "".join(
                random.choices(string.ascii_lowercase + string.digits, k=6)
            )
            if self.phone_number:
                temp_username = f"user_{self.phone_number[-4:]}_{random_str}"
            else:
                temp_username = f"user_no_phone_{random_str}"
            while User.objects.filter(username=temp_username).exists():
                temp_username = f"{temp_username}{random.randint(0, 9)}"
            self.username = temp_username

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

    skill_level = models.CharField(max_length=100)
    bio = models.TextField(blank=True, null=True)
    division = models.CharField(max_length=100, blank=True, null=True)
    user_metrics = models.JSONField(blank=True)
    # Address
    address = models.JSONField(blank=True)
    # Contacts
    social_media = models.JSONField(blank=True)

    created_time = models.DateTimeField(auto_now_add=True, null=True)
    updated_time = models.DateTimeField(auto_now=True, null=True)


    class Meta:
        db_table = "sportsman"

    def __str__(self):
        return f"Sportsman {self.user.first_name} - {self.user.last_name}"

    # # Here all media associated to sportsman will be deleted
    # def delete(self, *args, **kwargs):
    #     media_objects = self.media.all()

    #     for media in media_objects:
    #         media.delete()
        
    #     super().delete(*args, **kwargs)
            

class Trainer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='trainer_profile')
    sport = models.ForeignKey(Sport, on_delete=models.CASCADE, related_name="trainers", blank=True, null=True)
    
    skill_level = models.CharField(max_length=100)
    bio = models.TextField(blank=True, null=True)
    division = models.CharField(max_length=100, blank=True, null=True)
    user_metrics = models.JSONField(blank=True)
    # Address
    address = models.JSONField(blank=True, null=True)
    # Contacts
    social_media = models.JSONField(blank=True, null=True)

    created_time = models.DateTimeField(auto_now_add=True, null=True)
    updated_time = models.DateTimeField(auto_now=True, null=True)


    # General Results
    # number_of_games = models.PositiveIntegerField(blank=True, null=True)
    # number_of_students = models.PositiveIntegerField(blank=True, null=True)
    # number_of_awards = models.PositiveIntegerField(blank=True, null=True)

    class Meta:
        db_table = "trainer"

    def __str__(self):
        return f"Trainer {self.user.first_name} - {self.user.last_name}"

    # def delete(self, *args, **kwargs):
    #     media_objects = self.media.all()

    #     for media in media_objects:
    #         media.delete()
        
    #     super().delete(*args, **kwargs)


class UserMedia(BaseMedia):
    user = models.ManyToManyField(User, related_name='media')
