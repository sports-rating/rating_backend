import pytest
from datetime import date
from typing import Generator

from rest_framework.test import APIClient

from sport.models import (
    Sport, 
    Tournament
)

@pytest.fixture()
def api_client() -> Generator[APIClient, None, None]:
    """
    Fixture to provide an API client
    """
    yield APIClient()


@pytest.fixture
def sport(db):
    """
    Fixture to create a Sport instance
    """
    return Sport.objects.create(name="Football")


@pytest.fixture
def tournament(db, sport):
    """
    Fixture to create a Tournament instance
    """
    return Tournament.objects.create(
        name="Champions League",
        start_time=date(2025, 6, 10),
        place="London",
        division="Pro League",
        sport=sport, # FK to Sport model
    )


@pytest.fixture
def tournament_serializer_data(sport) -> dict:
    """
    Fixture to provide tournament serializer data
    """
    return {
        "name": "Champions League",
        "start_time": date(2025, 6, 10),
        "place": "London",
        "division": "Pro League",
        "sport_id": sport.id
    }

@pytest.fixture
def tournament_payload(sport) -> dict:
    """
    Request payload for Tournament
    """
    return {
        "name": "Premier League",
        "start_time": date(2022, 6, 10),
        "place": "London",
        "division": "Pro League",
        "sport_id": sport.id
    }

@pytest.fixture
def tournament_response() -> dict:
    """
    Response data for Tournament
    """
    return {
        "name": "Premier League",
        "start_time": str(date(2022, 6, 10)),
        "place": "London",
        "division": "Pro League",
        "sport": {
            "name": "Football",
            "logo": None
        },
        "logo": None,
    }

