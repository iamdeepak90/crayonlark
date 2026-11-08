from __future__ import annotations

from functools import lru_cache

import redis

from crayonlark.core.config import get_settings


@lru_cache
def get_redis() -> redis.Redis:
    return redis.Redis.from_url(get_settings().redis_url, decode_responses=True)
