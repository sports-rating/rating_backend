import uuid
import string
import random
import typing as t
import os
from uuid import UUID
from datetime import timedelta, datetime

import pytz
import requests

from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.functional import SimpleLazyObject
from django.db.models import Case, When, IntegerField
from django.utils.deconstruct import deconstructible

from rest_framework import status
from rest_framework.response import Response

from firebase_admin import messaging

from shared.addons.custom_logging import log


DATETIME_FORMAT: str = "%Y-%m-%d %H:%M:%S"


def generate_token():
    return str(uuid.uuid4())

def generate_verification_code():
    return "".join(random.choices(string.digits, k=6))


def success_response(data=None, message="Success", code=status.HTTP_200_OK):
    return Response(
        {"success": True, "code": code, "message": _(message), "data": data},
        status=code,
    )


def error_response(
    data=None,
    message="Error",
    code=status.HTTP_400_BAD_REQUEST,
):
    return Response(
        {"success": False, "code": code, "message": _(message), "data": data},
        status=code,
    )


@deconstructible
class CorrectPath:
    def __init__(self, base_path, owner=None):
        self.base_path = base_path
        self.owner = owner
    
    def __call__(self, instance, filename):
        print(filename)
        print(self.owner)
        if self.owner == "sportsman":   
            return os.path.join("sportsman/profile", filename)
        elif self.owner == "trainer":
            return os.path.join("trainer/profile", filename)
        else:
            return os.path.join(self.base_path, filename)