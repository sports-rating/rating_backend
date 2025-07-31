import uuid
import os
import mimetypes

from django.db import models
from apps.shared.utils.enums import MediaChoices 
from apps.shared.utils.utils import CorrectPath



class BaseModel(models.Model):
    id = models.UUIDField(
        unique=True, default=uuid.uuid4, editable=False, primary_key=True
    )
    created_time = models.DateTimeField(auto_now_add=True, null=True)
    updated_time = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        abstract = True


class BaseMedia(BaseModel):
    media_type = models.CharField(max_length=100, choices=MediaChoices.choices(), default=MediaChoices.IMAGE.value)
    file = models.FileField(upload_to=CorrectPath('media'), null=True)
    size = models.PositiveIntegerField(null=True, blank=True)
    extension = models.CharField(max_length=10, blank=True)

    class Meta:
        abstract=True

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


class Country(BaseModel):
    name = models.CharField(max_length=100)

    class Meta:
        db_table = "country"
        indexes = [
            models.Index(fields=["name"]),
        ]
        verbose_name = "Country"
        verbose_name_plural = "Countries"
    
    def __str__(self):
        return self.name
    

class Region(BaseModel):
    name = models.CharField(max_length=100)
    
    class Meta:
        db_table = "region"
        indexes = [
            models.Index(fields=["name"])
        ]
        verbose_name = "Region"
        verbose_name_plural = "Regions"

    def __str__(self):
        return self.name
    

class District(BaseModel):
    name = models.CharField(max_length=100)
    region = models.ForeignKey(Region, on_delete=models.CASCADE, related_name="districts")

    class Meta:
        db_table = "district"
        unique_together = ("name", "region")
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["region"]),
        ]
        verbose_name = "District"
        verbose_name_plural = "Districts"
    
    def __str__(self):
        return f"{self.name}, {self.region.name}"


class Neighborhood(BaseModel):
    name = models.CharField(max_length=100)
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name="neighborhoods")

    class Meta:
        db_table = "neighborhood"
        unique_together = ("name", "district")
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["district"]),
        ]
        verbose_name = "Neighborhood"
        verbose_name_plural = "Neighborhoods"
    
    def __str__(self):
        return f"{self.name}, {self.district.name} ({self.district.region.name})"
