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


def get_file_full_url(url):
    """
    Get the full URL of a file.
    """
    url = str(url)
    url = url.lstrip("/")
    if not url.startswith("media"):
        url = "media/" + url
    return f"{settings.BACKEND_URL.rstrip('/')}/{url}"
