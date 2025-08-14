import pytest
from datetime import date
from typing import Any

from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from shared.addons.exceptions import CustomValidationError
from shared.addons.custom_logging import logger


@pytest.mark.django_db
class TestUserRegistrationView:

    def test_factories(
            self,
            sport_factory,
            tournament_factory
        ) -> None:
        """
        Testing factories
        """
        sport = sport_factory()
        tournament = tournament_factory(sport=sport)
        assert tournament.sport == sport

    def test_trainer_registration(
            self,
            api_client: APIClient,
            sport_factory,
            school_factory,
            tournament_factory,
            trainer_payload: dict
        ):
        """
        Testing trainer registration
        """
        sport_1 = sport_factory()
        sport_2 = sport_factory()
        school = school_factory()
        school.sports.add(sport_1, sport_2)
        tournament = tournament_factory(sport=sport_1)

        trainer_payload["educations"][0]["school_id"] = school.id
        trainer_payload["educations"][0]["sport_id"] = sport_1.id
        trainer_payload["results"][0]["tournament_id"] = tournament.id
        trainer_payload["trainer_profile"]["sport_id"] = sport_1.id

        response_create = api_client.post('/api/user/profile/trainer/', data=trainer_payload, format='json')
        assert response_create.status_code == 200

        # logger.info(response_create.data)
        trainer_id = response_create.data["data"]["id"]
        logger.info(f"Trainer id: {trainer_id}")

        return {
            "school_id": school.id,
            "sport_id": sport_1.id,
            "tournament_id": tournament.id,
            "trainer_id": trainer_id,
        }

    def test_sportsman_registration(
            self,
            api_client: APIClient,
            sport_factory,
            school_factory,
            tournament_factory,
            sportsman_payload: dict,
            trainer_payload: dict,
            trainer_registration: dict[str, Any]
        ):
        """
        Testing sportsman registration
        """
        sport_1 = sport_factory()
        sport_2 = sport_factory()
        school = school_factory()
        school.sports.add(sport_1, sport_2)
        tournament = tournament_factory(sport=sport_2)

        trainer_id = trainer_registration["trainer_id"]
        sportsman_payload["educations"][0]["school_id"] = school.id
        sportsman_payload["educations"][0]["sport_id"] = sport_1.id
        sportsman_payload["results"][0]["tournament_id"] = trainer_registration["tournament_id"]
        sportsman_payload["results"][0]["trainer_id"] = trainer_registration["trainer_id"]
        sportsman_payload["results"][1]["tournament_id"] = tournament.id
        sportsman_payload["results"][1]["trainer_id"] = trainer_registration["trainer_id"]
        sportsman_payload["sportsman_profile"]["sport_id"] = trainer_registration["sport_id"]
        sportsman_payload["sportsman_profile"]["trainer_id"] = trainer_registration["trainer_id"]

        response_create = api_client.post('/api/user/profile/sportsman/', data=sportsman_payload, format='json')
        assert response_create.status_code == 200

        # get trainer profile (if results are updated)
        response_get = api_client.get(f'/api/user/profile/trainer/{trainer_id}/', format="json")
        assert response_get.status_code == 200

        logger.info(response_get.data)
