from celery import shared_task
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.shared.utils.logging import logger
from apps.shared.services.scoring_service import ScoringService


@shared_task
def recalculate_user_points_task(tournament_id):
    """
    Recalculates points for all sportsmen and their trainers in a tournament.
    """
    logger.info(f"Recalculating user points for tournament {tournament_id}...")
    ScoringService.recalculate_points_for_tournament(tournament_id)
