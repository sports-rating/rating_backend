import json

from redis import Redis
from django.conf import settings


redis_connection: Redis = None


def get_redis_connection() -> Redis:
    global redis_connection

    if redis_connection is None:
        redis_connection = Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
            db=0,
            decode_responses=True,  # Ensure that responses are decoded to strings
        )

    return redis_connection


def get_unique_visitors(date_str: str) -> int:
    """
    Get the count of unique visitors for a given date.
    """
    redis_conn = get_redis_connection()
    key = f"unique_visitors:{date_str}"
    return redis_conn.pfcount(key)


def get_unique_authenticated_users(date_str: str) -> int:
    """
    Get the count of unique authenticated users for a given date.
    """
    redis_conn = get_redis_connection()
    key = f"unique_auth_users:{date_str}"
    return redis_conn.pfcount(key)


def get_media_to_update_set(date_str: str) -> set:
    """
    Retrieve the set of medias that need their view counts updated for a given date.
    """
    redis_conn = get_redis_connection()
    key = f"media_to_update:{date_str}"
    return redis_conn.smembers(key)


def get_media_view_count(media_id: str, date_str: str) -> int:
    """
    Get the view count for a specific media on a given date.
    """
    redis_conn = get_redis_connection()
    key = f"media_views:{media_id}:{date_str}"
    return redis_conn.pfcount(key)
