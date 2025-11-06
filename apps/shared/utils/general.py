from attrs import field
import openpyxl
import typing as t

import logging
import os
import requests
import jwt
import datetime
import math
import re
import tempfile
import phonenumbers
from dateutil import relativedelta
from phonenumbers.phonenumberutil import NumberParseException
from PIL import Image
from io import BytesIO

from django.conf import settings
from django.utils.translation import gettext as _
from django.core.files.base import ContentFile

from apps.shared.utils.logging import logger
from apps.shared.utils.exceptions import raise_validation_error
from apps.shared.utils.enums import (
    UserRequestTypes
)
from apps.shared.utils.utils import send_sms_message


def get_file_full_url(url: str) -> str:
    """
    Get the full URL of a file.
    """
    url = str(url)
    url = url.lstrip("/")
    if not url.startswith("media"):
        url = "media/" + url
    return f"{settings.BACKEND_URL.rstrip('/')}/{url}"


def get_file_relative_path(file) -> str:
    """
    Get relative path from media root (media/filename.mp4)
    This works everywhere because it's relative
    """
    if not file:
        return None
    return file.name


def get_container_path(relative_path: str) -> str:
    """
    Convert relative path to absolute path in current container
    """

    if relative_path.startswith('media/'):
        relative_path = relative_path[6:]

    if os.path.exists('/app/media'):
        return f"/app/media/{relative_path}"
    elif os.path.exists('/media'):
        return f"/media/{relative_path}"
    else:
        # Fallback to Django's MEDIA_ROOT
        return os.path.join(settings.MEDIA_ROOT, relative_path)


def calculate_file_size(size) -> str:
    """
    Calculate the file size in a human-readable format.
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} TB"


def check_uniqueness(field_name, data, model, instance=None):
    """
    Related to Models!
    Check the uniqueness of a field in a model.
    """
    if field_name in data:
        value = data[field_name]
        if value and model.objects.exclude(pk=getattr(instance, 'pk', None)).filter(**{field_name: value}).exists():
            raise_validation_error(message=_(f"{(model.__name__).capitalize()} with this {field_name.replace('_', ' ')} already exists!"))


def check_m2m_uniqueness(field_name, data, model, instance=None, error_field_name=None):
    """
    Check if any of the M2M related objects already exist for another instance.

    :param field_name: Name of the M2M field (e.g., "sports")
    :param data: dict with input data (validated_data from serializer)
    :param model: Model class (e.g., Federation)
    :param instance: Current instance if update
    :param error_field_name: Optional field name for error key (defaults to field_name)
    """
    if field_name not in data:
        return

    values = data[field_name]
    if not values:
        return

    # Get IDs for comparison
    ids = [v.id if hasattr(v, 'id') else v for v in values]
    qs = model.objects.filter(**{f"{field_name}__in": ids})
    if instance:
        qs = qs.exclude(pk=instance.pk)

    if qs.exists():
        # Find which related objects conflict
        related_model = model._meta.get_field(field_name).related_model
        conflicting_objs = related_model.objects.filter(id__in=ids, **{model._meta.model_name + "s__in": qs}).distinct()
        names = ", ".join(str(obj.get_name) for obj in conflicting_objs)
        raise_validation_error(message=_(f"{model.__name__} already exists for {field_name}: {names}"))


def check_phone_valid(phone_number: str) -> None:
    if phone_number:
        try:
            parsed_number = phonenumbers.parse(phone_number)
            if not phonenumbers.is_valid_number(parsed_number):
                raise_validation_error(message=_("Please enter a valid phone number."))
        except NumberParseException:
            raise_validation_error(message=_("Please enter a valid phone number."))


def request_type_theme_mapping(request_type):
    """
    Map user request types to their corresponding themes.
    """
    mapping = {
        UserRequestTypes.FEDERATION_ADMIN_REQUEST.value: "Join Federation as Admin",
        UserRequestTypes.TRAINER_FEDERATION_REQUEST.value: "Join Federation as Trainer",
        UserRequestTypes.TRAINER_WORKPLACE_VERIFICATION_REQUEST.value: "Trainer Workplace Verification",
    }
    return mapping.get(request_type, "Unknown Request Type")


def send_sport_institution_message(school_name: str, phone_number: str, status: str) -> int:
    if status == "approved":
        text = _("Your request to register the sport institution '%(school_name)s' has been approved. "
                "You can now log in and start using our services.") % {
            "school_name": school_name
        }
    else:
        text = _("Your request to register the sport institution '%(school_name)s' has been rejected. "
                "For more information, please contact support.") % {
            "school_name": school_name
        }
    return send_sms_message(phone_number, text)


def compress_image(image):
    """
    Compress the image to reduce its size.
    """
    try:
        # Ensure file is open for reading
        image.open('rb')

        img = Image.open(BytesIO(image.read()))
        img.load()  # Force load to verify it's a valid image

        # convert to RGB
        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGB")

        max_size = settings.IMAGE_DIMENSION
        img.thumbnail(max_size, Image.Resampling.LANCZOS)

        temp_img = BytesIO()
        img.save(temp_img, format='JPEG', quality=85, optimize=True)
        temp_img.seek(0)

        # Change image extension to .jpg
        base_name = os.path.basename(image.name)
        if '.' in base_name:
            base_name = base_name.rsplit('.', 1)[0]
        new_filename = f"{base_name}.jpg"
        return ContentFile(temp_img.getvalue(), name=new_filename)

    except Exception as e:
        raise ValueError(f"Image compression failed: {e}")

    finally:
        try:
            image.close()
        except Exception:
            pass
