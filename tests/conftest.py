import pytest
from pytest_factoryboy import register
from datetime import date
from typing import Generator

from rest_framework.test import APIClient


from tests.factories import (
    ResultFactory,
    SportFactory,
    SchoolFactory,
    TournamentFactory
)

register(ResultFactory)
register(SportFactory)
register(SchoolFactory)
register(TournamentFactory)
