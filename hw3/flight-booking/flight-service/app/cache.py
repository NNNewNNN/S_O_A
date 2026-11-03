import json
import logging
from typing import Any, Optional

from redis.sentinel import Sentinel

from app.config import REDIS_MASTER, REDIS_SENTINELS

logger = logging.getLogger("cache")

sentinels = [(h, int(p)) for h, p in (s.split(":") for s in REDIS_SENTINELS.split(","))]
sentinel = Sentinel(sentinels, socket_timeout=2)

FLIGHT_TTL = 600
SEARCH_TTL = 300


def _get_master():
    try:
        return sentinel.master_for(REDIS_MASTER, socket_timeout=2)
    except Exception as e:
        logger.warning(f"Redis unavailable: {e}")
        return None


def flight_key(flight_id: str) -> str:
    return f"flight:{flight_id}"


def search_key(origin: str, destination: str, date: Optional[str]) -> str:
    return f"search:{origin}:{destination}:{date or 'any'}"


def get(key: str) -> Optional[Any]:
    r = _get_master()
    if not r:
        return None
    try:
        val = r.get(key)
        if val:
            logger.info(f"CACHE HIT: {key}")
            return json.loads(val)
        logger.info(f"CACHE MISS: {key}")
        return None
    except Exception as e:
        logger.warning(f"cache get failed: {e}")
        return None


def set(key: str, value: Any, ttl: int) -> None:
    r = _get_master()
    if not r:
        return
    try:
        r.setex(key, ttl, json.dumps(value, default=str))
    except Exception as e:
        logger.warning(f"cache set failed: {e}")


def invalidate(*keys: str) -> None:
    r = _get_master()
    if not r:
        return
    try:
        for k in keys:
            r.delete(k)
            logger.info(f"CACHE INVALIDATE: {k}")
    except Exception as e:
        logger.warning(f"cache invalidate failed: {e}")


def invalidate_search_for(origin: str, destination: str) -> None:
    r = _get_master()
    if not r:
        return
    try:
        pattern = f"search:{origin}:{destination}:*"
        batch = []
        for key in r.scan_iter(match=pattern, count=100):
            batch.append(key)
            if len(batch) >= 100:
                r.delete(*batch)
                batch = []
        if batch:
            r.delete(*batch)
        logger.info(f"CACHE INVALIDATE pattern: {pattern}")
    except Exception as e:
        logger.warning(f"cache invalidate_search failed: {e}")