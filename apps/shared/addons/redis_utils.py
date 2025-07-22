import json

from redis import Redis

from django.conf import settings
from shared.addons.utils import logger

redis_connection: Redis = None


def get_redis_connection() -> Redis:
    global redis_connection

    if redis_connection is None:
        redis_connection = Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
            db=0,
        )

    return redis_connection