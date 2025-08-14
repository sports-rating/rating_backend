import pytest
from datetime import date

from django.core.files.uploadedfile import SimpleUploadedFile

from shared.addons.exceptions import CustomValidationError
from shared.addons.custom_logging import logger


@pytest.mark.django_db
class TestTournamentView:

    def test_create(self, api_client, tournament_payload) -> None:
        """
        Testing create method
        """
        # create a new tournament
        response_create = api_client.post('/api/sport/tournament/', data=tournament_payload, format='json')
        logger.info(response_create.data)
        assert response_create.status_code == 200
        assert response_create.data['data']['name'] == tournament_payload["name"]

        # read the newly created tournament
        response_read = api_client.get('/api/sport/tournament/', format='json')
        assert response_read.status_code == 200
        assert response_read.data['data'][0]['name'] == tournament_payload['name']

    def test_get(self, api_client, tournament_response, tournament_payload) -> None:
        """
        Testing the expected response payload
        """
        # create a tournament
        response_create = api_client.post('/api/sport/tournament/', data=tournament_payload, format='json')
        assert response_create.status_code == 200

        # get a tournament
        tournament_id = response_create.data['data']['id']
        response_get = api_client.get(f'/api/sport/tournament/{tournament_id}/', format='json')
        assert response_get.status_code == 200
        logger.info(response_get.data)
        response_get.data['data'].pop('id')
        response_get.data['data']['sport'].pop('id')
        assert response_get.data['data'] == tournament_response

    def test_update(self, api_client, tournament_payload) -> None:
        """
        Testing update method
        """
        # create a tournament
        response_create = api_client.post('/api/sport/tournament/', data=tournament_payload, format='json')
        assert response_create.status_code == 200
        assert response_create.data['data']['name'] == tournament_payload["name"]

        # update the tournament
        tournament_id = response_create.data['data']['id']
        tournament_payload["name"] = "France League"
        response_update = api_client.put(f'/api/sport/tournament/{tournament_id}/', data=tournament_payload, format='json')
        assert response_update.status_code == 200
        assert response_update.data['data']['name'] == tournament_payload['name']

        # update non existing tournament
        response_update = api_client.put(f'/api/sport/tournament/{tournament_id}af/', data=tournament_payload, format='json')
        assert response_update.status_code == 404

    def test_delete(self, api_client, tournament_payload):
        """
        Testing delete method
        """
        # create a tournament
        response_create = api_client.post('/api/sport/tournament/', data=tournament_payload, format='json')
        assert response_create.status_code == 200
        assert response_create.data['data']['name'] == tournament_payload["name"]

        # delete the tournament
        tournament_id = response_create.data['data']['id']
        response_delete = api_client.delete(f'/api/sport/tournament/{tournament_id}/')
        assert response_delete.status_code == 204

        # read the tournament to ensure it was deleted
        response_read = api_client.get(f'/api/sport/tournament/{tournament_id}/', format='json')
        assert response_read.status_code == 404
