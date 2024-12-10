import random
import string

import phonenumbers
from PIL import Image
from django.core.validators import FileExtensionValidator

from django.db import models
from django.contrib.auth.models import AbstractUser

from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.tokens import RefreshToken

from phonenumbers.phonenumberutil import NumberParseException
from shared.models import BaseModel
from core.settings import IMAGE_DIMENSION


class User(AbstractUser, BaseModel):
    first_name = models.CharField(max_length=100, null=True, blank=True)
    last_name = models.CharField(max_length=100, null=True, blank=True)
    phone_number = models.CharField(max_length=13)
    email = models.CharField(null=True, blank=True)
    photo = models.ImageField(
        upload_to="user/images",
        validators=[
            FileExtensionValidator(allowed_extensions=["heic", "png", "jpg", "jpeg"])
        ],
        null=True,
        blank=True,
    )
    birth_date = models.DateField(null=True, blank=True)
    is_verified = models.BooleanField(default=False)

    class Meta:
        db_table = "user"
        ordering = ["-created_time"]

    def __str__(self):
        return self.username.title()
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.photo:
            try:
                image = Image.open(self.photo.path)
                desired_size = IMAGE_DIMENSION
                image.thumbnail(desired_size)
                # Save the resized image back to the same path
                image.save(self.photo.path)
            except Exception as e:
                print(f"Error resizing image: {e}")
    
    @property
    def full_name(self):
        return f"{self.last_name} {self.first_name}"

    def check_phone_valid(self):
        if self.phone_number:
            try:
                parsed_number = phonenumbers.parse(self.phone_number)
                print(parsed_number) # for checking
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