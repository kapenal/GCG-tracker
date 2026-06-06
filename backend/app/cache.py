"""In-memory TTL cache for read-heavy API responses."""

from __future__ import annotations

import logging
from time import monotonic
from typing import Any

logger = logging.getLogger(__name__)

CACHE_CONTROL_HEADER = "public, max-age=300"

TTL_SETS = 600
TTL_RARITIES = 600
TTL_CARDS = 300


class TTLCache:
    def __init__(self) -> None:
        self._entries: dict[str, tuple[float, Any]] = {}

    @staticmethod
    def _full_key(namespace: str, key: str) -> str:
        return f"{namespace}:{key}"

    def get(self, namespace: str, key: str = "") -> Any | None:
        full = self._full_key(namespace, key)
        entry = self._entries.get(full)
        if entry is None:
            return None
        expires_at, value = entry
        if monotonic() >= expires_at:
            del self._entries[full]
            return None
        return value

    def set(self, namespace: str, key: str, value: Any, ttl_seconds: int) -> None:
        full = self._full_key(namespace, key)
        self._entries[full] = (monotonic() + ttl_seconds, value)

    def invalidate_all(self) -> int:
        count = len(self._entries)
        self._entries.clear()
        if count:
            logger.info("API cache invalidated (%d entries)", count)
        return count


api_cache = TTLCache()


def invalidate_api_cache() -> None:
    api_cache.invalidate_all()
