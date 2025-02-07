import pytest 
from datetime import date

from django.core.files.uploadedfile import SimpleUploadedFile

from shared.addons.exceptions import CustomValidationError
from shared.addons.custom_logging import logger


@pytest.mark.django_db
class TestUserRegistrationView:

    def test_register(
            self, 
            api_client, 
            school_factory, 
            sport_factory, 
            tournament_factory
        ) -> None:
        """
        Testing registration
        """
        school = school_factory()
        sport = sport_factory()
        tournament = tournament_factory(sport=sport)
        logger.info(f"Here: {tournament} - {tournament.sport}")
        logger.info(f"Division: {tournament.division}")
        assert tournament.sport == sport
        
