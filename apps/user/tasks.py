from celery import shared_task
from datetime import date, timedelta

from django.utils import timezone
from django.utils.translation import gettext as _

from apps.shared.utils.logging import logger
from apps.shared.services.scoring_service import ScoringService
from apps.user.models import DailyUsers
from apps.shared.utils.redis_utils import get_redis_connection


redis_connection = get_redis_connection()


### TODO:CoderB7 This shared task is never used!
@shared_task
def recalculate_user_points_task(tournament_id):
    """
    Recalculates points for all sportsmen and their trainers in a tournament.
    """
    logger.info(f"Recalculating user points for tournament {tournament_id}...")
    ScoringService.recalculate_points_for_tournament(tournament_id)


@shared_task
def recalculate_all_users_points_task():
    """
    Recalculates points for all sportsmen and their trainers.
    """
    logger.info("Recalculating points for all users...")
    ScoringService.recalculate_all_points()


@shared_task
def store_daily_user_counts_task():
    """
    Stores daily user counts for analytics.
    """
    yesterday = date.today() - timedelta(days=1)

    unique_users_key = f"unique_visitors:{yesterday.strftime('%Y-%m-%d')}"
    unique_authenticated_users_key = f"unique_auth_users:{yesterday.strftime('%Y-%m-%d')}"

    try:
        unique_users_count = redis_connection.pfcount(unique_users_key)
        unique_authenticated_users_count = redis_connection.pfcount(unique_authenticated_users_key)

        DailyUsers.objects.update_or_create(
            date=yesterday,
            defaults={
                'unique_users': unique_users_count,
                'unique_authenticated_users': unique_authenticated_users_count
            }
        )

        logger.info(f"Stored daily user counts for {yesterday}: {unique_users_count} unique users, {unique_authenticated_users_count} unique authenticated users.")

    except Exception as e:
        logger.error(f"Error storing daily user counts for {yesterday}: {e}")

    return f"Stored daily user counts for {yesterday}"
