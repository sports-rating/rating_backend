from celery import shared_task
from datetime import date, timedelta

from django.db.models import F
from django.utils import timezone
from django.utils.translation import gettext as _
from django.db import transaction


from apps.shared.utils.logging import logger
from apps.shared.services.scoring_service import ScoringService
from apps.user.models import DailyUsers
from apps.shared.utils.redis_utils import get_redis_connection
from core.celery import app


redis_connection = get_redis_connection()


### TODO:CoderB7 This shared task is never used!
@app.task
def recalculate_user_points_task(tournament_id):
    """
    Recalculates points for all sportsmen and their trainers in a tournament.
    """
    logger.info(f"Recalculating user points for tournament {tournament_id}...")
    ScoringService.recalculate_points_for_tournament(tournament_id)


@app.task
def recalculate_all_users_points_task():
    """
    Recalculates points for all sportsmen and their trainers.
    """
    logger.info("Recalculating points for all users...")
    ScoringService.recalculate_all_points()


@app.task
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


@app.task
def update_media_view_counts_for_yesterday_task() -> str:
    """
    Updates view counts for all media items(video) for yesterday.
    """
    from apps.user.models import UserMedia
    from apps.sport.models import SportInstitutionMedia

    yesterday = date.today() - timedelta(days=1)

    # Fetch media_to_update set from redis for yesterday
    media_to_update_key = f"media_to_update:{yesterday.strftime('%Y-%m-%d')}"
    try:
        media = redis_connection.smembers(media_to_update_key)
        for media_str in media:
            logger.info(f"Processing media for view count update: {media_str}")
            media_id, model_name = media_str.split(':')
            media_views_key = f"media_views:{media_id}:{yesterday.strftime('%Y-%m-%d')}"
            try:
                count = redis_connection.pfcount(media_views_key)

                if count == 0:
                    continue  # no views, skip

                with transaction.atomic():
                    if model_name == 'UserMedia':
                        UserMedia.objects.filter(id=media_id).update(view_count=F('view_count') + count)
                        logger.info(f"Celery Task | Updated UserMedia ID {media_id} view count to {count}.")
                    elif model_name == 'SportInstitutionMedia':
                        SportInstitutionMedia.objects.filter(id=media_id).update(view_count=F('view_count') + count)
                        logger.info(f"Celery Task | Updated SportInstitutionMedia ID {media_id} view count to {count}.")
                    else:
                        logger.error(f"Unknown media model: {model_name}")

            except Exception as e:
                logger.error(f"Celery Task | Error updating view count for media ID {media_id}: {e}")

    except Exception as e:
        logger.error(f"Celery Task | Error fetching media to update for yesterday: {e}")

    return f"Updated view counts for media for {yesterday}"
