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
def sportsman_payload() -> dict:
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
                "country": "США",
                "year": "2024-12-26",
                "rating": 1,
                "currently_participating": False,
                "trainer_id": ""
            },
            {
                "tournament_id": "",
                "country": "Russia",
                "year": "2023-11-26",
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


@pytest.fixture
def trainer_payload() -> dict:
    return {
        "first_name": "Naseer",
        "middle_name": "Abdul",
        "last_name": "Rahim",
        "pinfl": "12345678901235",
        "birth_date": "2000-12-01",
        "phone_number": "+998935321372",
        "user_role": "trainer",
        "email": "naseer@gmail.com",
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
                "country": "США",
                "year": "2024-12-26",
                "rating": 2,
                "currently_participating": "true",
            },
        ],
        "trainer_profile": {
            "skill_level": "Любитель",
            "sport_id": "",
            "division": "Дивизион 1",
            "bio": "My name is TEST",
            "user_metrics": {
                "height": 185,
                "weight": 65
            },
            "address": {
                "region": "Санкт-Петербург",
                "city": "Город 2",
                "street": "test",
                "place_of_birth": "Россия",
                "citizenship": "Россия"
            }
        }
    }


@pytest.fixture
def trainer_registration(
        api_client,
        sport_factory,
        school_factory,
        tournament_factory,
        trainer_payload
    ):
    sport_1 = sport_factory()
    school = school_factory()
    school.sports.add(sport_1)
    tournament = tournament_factory(sport=sport_1)

    trainer_payload["educations"][0]["school_id"] = school.id
    trainer_payload["educations"][0]["sport_id"] = sport_1.id
    trainer_payload["results"][0]["tournament_id"] = tournament.id
    trainer_payload["trainer_profile"]["sport_id"] = sport_1.id

    response = api_client.post('/api/user/profile/trainer/', data=trainer_payload, format='json')
    assert response.status_code == 200
    trainer_id = response.data["data"]["id"]

    return {
        "school_id": school.id,
        "sport_id": sport_1.id,
        "tournament_id": tournament.id,
        "trainer_id": trainer_id,
    }
