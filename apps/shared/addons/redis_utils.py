import json

from redis import Redis

from django.conf import settings
from shared.addons.utils import logger

redis_connection: Redis = None


def get_redis_connection() -> Redis:
    global redis_connection

    if redis_connection is None:
        redis_connection = Redis(**settings.REDIS_CREDENTIALS)

    return redis_connection