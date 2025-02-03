import pytest
from datetime import date
from typing import Generator

from rest_framework.test import APIClient

from sport.models import Sport

@pytest.fixture()
def api_client() -> Generator[APIClient, None, None]:
    """
    Fixture to provide an API client
    """
    yield APIClient()




