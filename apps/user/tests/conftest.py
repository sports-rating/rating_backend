import pytest
from pytest_factoryboy import register
from datetime import date
from typing import Generator

from rest_framework.test import APIClient

from sport.models import (
    Sport, 
    Tournament
)

from user.models import (
    User, 
    Trainer,
    Sportsman
)

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

@pytest.fixture()
def api_client() -> Generator[APIClient, None, None]:
    """
    Fixture to provide an API client
    """
    yield APIClient()


@pytest.fixture
def user_payload() -> dict:
    """
    Request payload for User
    """
    return {
        "first_name": "Xurshid",
        "middle_name": "Akbar o'g'li",
        "last_name": "Rasulov",
        "pinfl": "12345678901234",
        "birth_date": "2004-12-01",
        "phone_number": "+998935321371",
        "user_role": "sportsman",
        "email": "xurshid@gmail.com",
        "gender": "male",
        "educations": [
            {
                "school_id": "",
                "sport_id": "",
                "start_year": "2018-06-11",
                "end_year": "2023-06-11",
                "currently_studying": True
            }
        ],
        "results": [
            {
                "tournament_id": "",
                "country": "Russia",
                "year": "2024-12-26",
                "rating": 1,
                "currently_participating": False,
                "trainer_id": ""
            },
            {
                "tournament_id": "",
                "country": "Russia",
                "year": "2024-12-26",
                "rating": 1,
                "currently_participating": False,
                "trainer_id": ""
            }
        ],
        "sportsman_profile": {
            "skill_level": "Professional",
            "sport_id": "",
            "trainer_id": "",
            "division": "1",
            "bio": "My name is Xurshid",
            "user_metrics": {
                "height": 185,
                "weight": 65
            },
            "address": {
                "region": "Tashkent",
                "city": "Tashkent",
                "street": "Tashselmash",
                "place_of_birth": "Uzbekistan",
                "citizenship": "Uzbekistan"
            }
        }
    }
