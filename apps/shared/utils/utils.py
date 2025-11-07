import uuid
import string
import random
import mimetypes
import typing as t
import os
import shutil
import base64
import hashlib
from uuid import UUID
from datetime import timedelta, datetime
from user_agents import parse as parse_user_agent

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
from rest_framework.request import Request

from firebase_admin import messaging

from apps.shared.utils.logging import logger
from apps.shared.utils.payloads import create_sms_payload


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
        guessed_type, _ = mimetypes.guess_type(filename)
        if guessed_type:
            if guessed_type.startswith("image/"):
                subfolder = "images"
            elif guessed_type.startswith("video/"):
                subfolder = "videos"
            else:
                subfolder = "files"
        else:
            subfolder = "files"

        # Distinguish by model name
        model_folder = instance.__class__.__name__.lower()
        return os.path.join(model_folder, subfolder, filename)

        # if self.owner == "sportsman":
        #     return os.path.join("sportsman/profile", filename)
        # elif self.owner == "trainer":
        #     return os.path.join("trainer/profile", filename)
        # elif self.owner == "user":
        #     return os.path.join("user/images", filename)
        # elif self.owner == "sport":
        #     return os.path.join("sport/", filename)
        # elif self.owner == "tournament":
        #     return os.path.join("tournament/", filename)
        # elif self.owner == "team":
        #     return os.path.join("team/logo/", filename)
        # elif self.owner == "school":
        #     return os.path.join("school/", filename)
        # else:
        #     return os.path.join(self.base_path, filename)


def parse_nested_querydict(querydict):
    """
    Recursively parse a QueryDict to handle nested keys like 'sportsman_profile[sport_type]'.
    """
    data = {}
    for key, value in querydict.lists():
        if "[" in key and "]" in key:
            keys = key.replace("]", "").split("[")
            d = data
            for k in keys[:-1]:
                d = d.setdefault(k, {})
            d[keys[-1]] = value[0] if len(value) == 1 else value
        else:
            data[key] = value[0] if len(value) == 1 else value
    return data


def handle_file_update(instance, field_name):
    """
    Handles file deletion when updating or deleting a model instance.
    """
    if instance.pk:
        try:
            old_instance = instance.__class__.objects.get(pk=instance.pk)
            old_file = getattr(old_instance, field_name, None)
            new_file = getattr(instance, field_name, None)
            if old_file and old_file != new_file:
                if os.path.isfile(old_file.path):
                    os.remove(old_file.path)
        except instance.__class__.DoesNotExist:
            pass  # Instance is being created for the first time


def handle_file_delete(instance, field_name):
    """
    Handles file deletion when deleting a model instance.
    """
    file = getattr(instance, field_name, None)
    if file and os.path.isfile(file.path):
        os.remove(file.path)


def send_sms_message(phone_number: str, text: str) -> int:
    response = requests.post(
        settings.PLAY_MOBILE_URL,
        json=create_sms_payload(phone_number, text),
        auth=(settings.PLAY_MOBILE_LOGIN, settings.PLAY_MOBILE_PASSWORD),
    )
    logger.info(f"SMS send to {phone_number}, response: {response.status_code} - {response.text}")  # LOGGING
    if response.status_code != 200:
        logger.error(f"Error on send_sms: {response.status_code=} {response.text=}")

    return response.status_code


def finalize_result_file(result, temp_file) -> str:
    """
    Copies the temporary file to the final media directory and returns the new file path.
    """
    correct_path = CorrectPath("media")
    filename = os.path.basename(temp_file.path)
    new_relative_path = correct_path(result, filename)
    new_full_path = os.path.join(settings.MEDIA_ROOT, new_relative_path)
    logger.info(f"Copying file to: {new_full_path}")
    os.makedirs(os.path.dirname(new_full_path), exist_ok=True)

    shutil.copy2(temp_file.path, new_full_path)
    return new_relative_path


def archive_old_file(file_field: t.Optional[t.Any]) -> t.Optional[str]:
    """
    Moves the old file to an archive directory:
        media/archive/YYYY/MM/DD/<filename>
    Adds suffix if a file with the same name exists.
    Args:
        file_field (t.Optional[t.Any]): The FileField or ImageField to archive.

    Returns:
        t.Optional[str]: The new relative path of the archived file, or None if archiving failed.
    """
    if not file_field or not getattr(file_field, "name", None):
        logger.info("No file to archive.")
        return None

    old_path = getattr(file_field, "path", None)
    if not old_path or not os.path.exists(old_path):
        logger.info("Old file does not exist.")
        return None

    # Create daily archive directory
    date_str = datetime.now().strftime("%Y/%m/%d")
    archive_dir = os.path.join(settings.MEDIA_ROOT, "archive", date_str)
    os.makedirs(archive_dir, exist_ok=True)

    # Build destination path
    base_name = os.path.basename(old_path)
    name, ext = os.path.splitext(base_name)
    new_path = os.path.join(archive_dir, base_name)

    # If file exists, add suffix
    counter = 1
    while os.path.exists(new_path):
        new_name = f"{name}_v{counter}{ext}"
        new_path = os.path.join(archive_dir, new_name)
        counter += 1

    # shutil.move with proper error handling
    try:
        shutil.move(old_path, new_path)

        # Verify the move worked
        if os.path.exists(new_path) and not os.path.exists(old_path):
            logger.info("✅ File successfully moved")
        else:
            logger.error("❌ File move failed - file still exists in original location")
            return None
    except Exception as e:
        logger.error(f"❌ File move failed: {e}")
        return None

    # Convert filesystem path to relative media URL
    relative_path = os.path.relpath(new_path, settings.MEDIA_ROOT)
    logger.info(f"Relative path: {relative_path}")
    return relative_path.replace("\\", "/")  # Ensure forward slashes


def get_user_hash(request: Request) -> t.Tuple[t.Optional[str], str]:
    """
    Generates a unique hash for the user based on their ID and User-Agent.
    """
    user_agent = request.META.get('HTTP_USER_AGENT', 'unknown')
    ip = request.META.get('REMOTE_ADDR', 'unknown')
    user_agent_parsed = parse_user_agent(user_agent)

    if user_agent_parsed.is_bot:
        return None, "Bot detected"  # Ignores bots

    user_base = f"{ip}:{user_agent}"
    user_hash = hashlib.sha256(user_base.encode('utf-8')).hexdigest()
    return user_hash, "Hash generated successfully"
