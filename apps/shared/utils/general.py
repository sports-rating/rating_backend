from attrs import field
import openpyxl

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

from django.conf import settings
from django.utils.translation import gettext as _

from apps.shared.utils.logging import logger
from apps.shared.utils.exceptions import raise_validation_error
from apps.shared.utils.enums import (
    UserRequestTypes
)


def get_file_full_url(url):
    """
    Get the full URL of a file.
    """
    url = str(url)
    url = url.lstrip("/")
    if not url.startswith("media"):
        url = "media/" + url
    return f"{settings.BACKEND_URL.rstrip('/')}/{url}"


def calculate_file_size(size):
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


def check_phone_valid(self, phone_number: str) -> None:
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
