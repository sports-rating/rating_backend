import uuid
import os
import mimetypes
import typing as t

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

    # defining Class variable using ClassVar annotation
    repr_fields: t.ClassVar[tuple[str, ...] | None] = None

    def __repr__(self) -> str:
        return self.to_string()

    def __str__(self) -> str:
        return self.to_string()

    def to_string(self) -> str:
        """
        Custom method for representing instance in string format
        """

        # default
        if self.repr_fields is None:
            return "{}<pk={}>".format(self.__class__.__name__, self.pk)

        # custom
        template: str = "{}<{}>"

        model_fields: tuple[str, ...] = tuple(
            field.name for field in self._meta.get_fields()
        )

        for repr_field in self.repr_fields:
            if repr_field not in model_fields:
                raise ValueError(
                    f"{repr_field} is not present in {self.__class__.__name__}"
                )

        key_value_pairs: tuple[str, ...] = tuple(
            f"{field}={getattr(self, field)}" for field in self.repr_fields
        )

        return template.format(
            self.__class__.__name__,
            ", ".join(key_value_pairs),
        )


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
