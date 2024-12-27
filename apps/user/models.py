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
from shared.models import BaseModel
from shared.addons.enums import GenderChoices, MediaChoices, UserRoles
from core.settings import IMAGE_DIMENSION
from shared.addons.utils import CorrectPath


class User(AbstractUser, BaseModel):
    first_name = models.CharField(max_length=100, null=True, blank=True)
    last_name = models.CharField(max_length=100, null=True, blank=True)
    middle_name = models.CharField(max_length=100, null=True, blank=True)
    
    user_role = models.CharField(max_length=50, choices=UserRoles.choices(), default=UserRoles.ORDINARY.value)
    phone_number = models.CharField(max_length=13)
    email = models.CharField(null=True, blank=True)
    # photo = models.ImageField(
    #     upload_to="user/images",
    #     validators=[
    #         FileExtensionValidator(allowed_extensions=["heic", "png", "jpg", "jpeg"])
    #     ],
    #     null=True,
    #     blank=True,
    # )
    photo = models.ManyToManyField('Media', related_name='user_profile', blank=True)
    birth_date = models.DateField(null=True, blank=True)
    is_verified = models.BooleanField(default=False)

    class Meta:
        db_table = "user"
        ordering = ["-created_time"]

    def __str__(self):
        return self.username.title()
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
        # if self.photo:
        #     try:
        #         image = Image.open(self.photo.path)
        #         desired_size = IMAGE_DIMENSION
        #         image.thumbnail(desired_size)
        #         # Save the resized image back to the same path
        #         image.save(self.photo.path)
        #     except Exception as e:
        #         print(f"Error resizing image: {e}")
    
    def delete(self, *args, **kwargs):
        # if self.photo:
        #     if os.path.isfile(self.photo.path):
        #         os.remove(self.photo.path)
        media_objects = self.photo.all()

        for media in media_objects:
            media.delete()

        if hasattr(self, 'sportsman_profile'):
            self.sportsman_profile.delete() # triggers delete method in Sportsman
        elif hasattr(self, 'trainer_profile'):
            self.trainer_profile.delete() # triggers delete method in Trainer
        super().delete(*args, **kwargs)

    @property
    def full_name(self):
        return f"{self.last_name} {self.first_name}"

    def check_phone_valid(self):
        if self.phone_number:
            try:
                parsed_number = phonenumbers.parse(self.phone_number)
                if not phonenumbers.is_valid_number(parsed_number):
                    raise ValidationError("Please enter a valid phone number.")
            except NumberParseException:
                raise ValidationError("Please enter a valid phone number.")
            
    def clean(self):
        self.check_username()
        self.check_phone_valid()
    
    def check_username(self):
        print(f"checking username for {self.username}")
        if not self.username:
            # Generate a fake username using random strings and phone number
            random_str = "".join(
                random.choices(string.ascii_lowercase + string.digits, k=6)
            )
            temp_username = f"user_{self.phone_number[-4:]}_{random_str}"
            while User.objects.filter(username=temp_username).exists():
                temp_username = f"{temp_username}{random.randint(0, 9)}"
            self.username = temp_username

    def tokens(self) -> dict[str, str]:
        refresh = RefreshToken.for_user(self)
        return dict(
            access=str(refresh.access_token),
            refresh=str(refresh),
        )


class Sportsman(BaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='sportsman_profile')
    sport_type = models.CharField(max_length=100)
    sport_direction = models.CharField(max_length=100)
    motto = models.CharField(max_length=100, blank=True, null=True)
    height = models.DecimalField(max_digits=5, decimal_places=2)
    weight = models.DecimalField(max_digits=5, decimal_places=2)
    gender = models.CharField(max_length=50, choices=GenderChoices.choices(), default=GenderChoices.MALE.value)
    # Address
    region = models.CharField(max_length=50)
    city = models.CharField(max_length=50)
    street = models.CharField(max_length=200)
    place_of_birth = models.CharField(max_length=100)
    citizenship = models.CharField(max_length=100)
    moving_date = models.DateField(blank=True, null=True)
    # Contacts
    telegram = models.URLField(blank=True, null=True)
    instagram = models.URLField(blank=True, null=True)
    media = models.ManyToManyField('Media', related_name='sportsmen', blank=True)
    
    class Meta:
        db_table = "sportsman"

    def __str__(self):
        return f"Sportsman {self.user.first_name} - {self.user.last_name}"

    # Here all media associated to sportsman will be deleted
    def delete(self, *args, **kwargs):
        media_objects = self.media.all()

        for media in media_objects:
            media.delete()
        
        super().delete(*args, **kwargs)
            

class Trainer(BaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='trainer_profile')
    sport_type = models.CharField(max_length=100)
    sport_direction = models.CharField(max_length=100)
    motto = models.CharField(max_length=100, blank=True, null=True)
    height = models.DecimalField(max_digits=5, decimal_places=2)
    weight = models.DecimalField(max_digits=5, decimal_places=2)
    gender = models.CharField(max_length=50, choices=GenderChoices.choices(), default=GenderChoices.MALE.value)
    # Address
    region = models.CharField(max_length=50)
    city = models.CharField(max_length=50)
    street = models.CharField(max_length=200)
    place_of_birth = models.CharField(max_length=100)
    citizenship = models.CharField(max_length=100)
    moving_date = models.DateField(blank=True, null=True)
    # General Results
    number_of_games = models.PositiveIntegerField()
    number_of_students = models.PositiveIntegerField()
    number_of_awards = models.PositiveIntegerField()
    # Contacts
    telegram = models.URLField(blank=True, null=True)
    instagram = models.URLField(blank=True, null=True)
    media = models.ManyToManyField('Media', related_name='trainer', blank=True)

    class Meta:
        db_table = "trainer"

    def delete(self, *args, **kwargs):
        media_objects = self.media.all()

        for media in media_objects:
            media.delete()
        
        super().delete(*args, **kwargs)


class Education(BaseModel):
    name = models.CharField(max_length=250)
    sport_type = models.CharField(max_length=100)
    start_year = models.DateField()
    end_year = models.DateField()
    currently_studying = models.BooleanField(default=False)
    
    sportsman_profile = models.ForeignKey(Sportsman, on_delete=models.CASCADE, related_name="educations", blank=True, null=True)
    trainer_profile = models.ForeignKey(Trainer, on_delete=models.CASCADE, related_name="educations", blank=True, null=True)

    class Meta:
        db_table = "school"


class Result(BaseModel):
    tournament_name = models.CharField(max_length=255)
    country = models.CharField(max_length=100)
    # start_year = models.DateField()
    # end_year = models.DateField()
    year = models.DateField(blank=True, null=True)
    currently_participating = models.BooleanField(default=False)
    rating = models.IntegerField(null=True, blank=True)
    logo = models.ImageField(upload_to='user/tournaments/', null=True, blank=True)
    
    sportsman_profile = models.ForeignKey(Sportsman, on_delete=models.CASCADE, related_name="results", blank=True, null=True)
    trainer_profile = models.ForeignKey(Trainer, on_delete=models.CASCADE, related_name="results", blank=True, null=True)

    class Meta:
        db_table = "result"

    def __str__(self):
        return self.tournament_name

    # def save(self, *args, **kwargs):
    #     super().save(*args, **kwargs)
    #     if self.logo:
    #         try:
    #             image = Image.open(self.logo.path)
    #             desired_size = IMAGE_DIMENSION
    #             image.thumbnail(desired_size)
    #             # Save the resized image back to the same path
    #             image.save(self.logo.path)
    #         except Exception as e:
    #             print(f"Error resizing logo: {e}")
    def delete(self, *args, **kwargs):
        if self.logo:
            if os.path.isfile(self.logo.path):
                os.remove(self.logo.path)
        super().delete(*args, **kwargs)


class Media(BaseModel):
    media_type = models.CharField(max_length=100, choices=MediaChoices.choices(), default=MediaChoices.IMAGE.value)
    file = models.FileField(upload_to=CorrectPath('media'))
    size = models.PositiveIntegerField(null=True, blank=True)
    extension = models.CharField(max_length=10, blank=True)

    def save(self, *args, **kwargs):
        if self.file and hasattr(self.file, 'file'):
            self.size = self.file.size
           
            _, ext = os.path.splitext(self.file.name)
            self.extension = ext.lower().lstrip('.')
           
            guessed_type, _ = mimetypes.guess_type(self.file.name)
            if guessed_type:
                if guessed_type.startswith("image/"):
                    self.media_type = MediaChoices.IMAGE.value
                elif guessed_type.startswith("video/"):
                    self.media_type = MediaChoices.VIDEO.value
                else:
                    self.media_type = MediaChoices.PDF.value        
        super().save(*args, **kwargs)  # Final save to ensure the object is saved

    def delete(self, *args, **kwargs):
        print(self.file)
        if self.file:
            print(self.file.path)
            if os.path.isfile(self.file.path):
                os.remove(self.file.path)
        super().delete(*args, **kwargs)
