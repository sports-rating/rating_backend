import pytest

from django.core.exceptions import ValidationError
from sport.models import Tournament
from shared.addons.custom_logging import logger

@pytest.mark.django_db
def test_tournament_creation(tournament):
    """
    Test that a Tournament instance is created correctly
    """
    assert Tournament.objects.count() == 1
    assert tournament.name == "Champions League"
    assert tournament.sport.name == "Football"


@pytest.mark.django_db
def test_tournament_required_fields():
    """
    Test that required fields must be provided
    """
    tournament = Tournament(name=None, start_time=None, place=None)

    with pytest.raises(ValidationError) as e:
        tournament.full_clean()

    logger.error(e.value)
    assert "This field cannot be null" in str(e.value)
