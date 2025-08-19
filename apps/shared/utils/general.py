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
from dateutil import relativedelta

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


def request_type_theme_mapping(request_type):
    """
    Map user request types to their corresponding themes.
    """
    mapping = {
        UserRequestTypes.FEDERATION_ADMIN_REQUEST.value: "Join Federation as Admin",
        UserRequestTypes.TRAINER_FEDERATION_REQUEST.value: "Join Federation as Trainer",
    }
    return mapping.get(request_type, "Unknown Request Type")
