import pytest
from datetime import date

# from rest_framework.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile

from shared.addons.exceptions import CustomValidationError
from shared.addons.custom_logging import logger
from sport.models import (
    Tournament,
    Team,
    Sport
)
from sport.serializers import (
    TournamentCreateSerializer,
    TournamentSerializer,
)


@pytest.mark.django_db
def test_tournament_create_serializer(tournament):
    """
    Test Tournament Create Serializer
    """



@pytest.mark.django_db(transaction=True)
class TestTournamentSerializer:

    def test_create_validate_serializer(self, sport, tournament, tournament_serializer_data) -> None:
        """
        Tests create validate method in TournamentCreateSerializer
        """
        serializer = TournamentCreateSerializer(data=tournament_serializer_data)

        with pytest.raises(CustomValidationError) as e:
            serializer.is_valid(raise_exception=True)

        logger.info(f"{e.value}")
        assert "Tournament with this name and year already exists!" in str(e.value)


    def test_update_validate_serializer(self, sport, tournament, tournament_serializer_data) -> None:
        """
        Tests update validate method in TournamentCreateSerializer
        """
        tournament_instance = Tournament( # this will be updated to tournament fixture's data
            name="France League",
            start_time=date(2024, 6, 10),
            place="London",
            division="Pro League",
            sport=sport
        )

        serializer = TournamentCreateSerializer(tournament_instance, data=tournament_serializer_data)

        with pytest.raises(CustomValidationError) as e:
            serializer.is_valid(raise_exception=True)

        logger.info(e.value)
        assert "Tournament with this name and year already exists!" in str(e.value)


    def test_create_serializer(self, sport, tournament_serializer_data) -> None:
        """
        Tests create method of TournamentCreateSerializer
        """
        serializer = TournamentCreateSerializer(data=tournament_serializer_data)
        assert serializer.is_valid(), serializer.errors

        tournament = serializer.save()
        assert Tournament.objects.count() == 1
        assert tournament.name == "Champions League"
        assert tournament.sport == sport


    def test_create_serializer_with_image(self, sport, tournament_serializer_data) -> None:
        with open("/home/userb/Pictures/Work/Testing/mechazilla.jpg", "rb") as image_file:
            image_content = image_file.read()

        image_file = SimpleUploadedFile(
            name='test_logo.jpg',
            content=image_content,
            content_type="image/jpeg",
        )

        tournament_serializer_data['logo'] = image_file

        serializer = TournamentCreateSerializer(data=tournament_serializer_data)
        assert serializer.is_valid(), serializer.errors

        tournament = serializer.save()

        assert tournament.logo.name.startswith("tournament/logos/test_logo")
        assert tournament.logo.name.endswith(".jpg")


    def test_get_tournament_to_representation(self, sport, tournament) -> None:
        serializer = TournamentSerializer(instance=tournament)
        data = serializer.data
        logger.info(date(2025, 6, 10))
        result = {
            "id": data.get("id"),
            "name": "Champions League",
            "start_time": str(date(2025, 6, 10)),
            "place": "London",
            "division": "Pro League",
            "logo": None,
            "sport": {
                "id": data["sport"].get("id"),
                "name": "Football",
                "logo": None
            }
        }

        assert data == result
