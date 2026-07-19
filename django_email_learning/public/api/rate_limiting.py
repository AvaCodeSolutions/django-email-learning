from django.core.cache import cache
from django.http import HttpRequest


def get_client_ip(request: HttpRequest) -> str:
    return request.META.get("REMOTE_ADDR", "unknown")


def is_rate_limited(key: str, *, limit: int, window_seconds: int) -> bool:
    """Fixed-window request counter backed by Django's cache framework.

    Returns True once `limit` calls for `key` have been seen within the
    current `window_seconds` window. Relies on whatever CACHES backend is
    configured; a per-process LocMemCache under-counts across multiple
    worker processes, so a shared backend (e.g. Redis) is recommended in
    production for this to be effective.
    """
    count = cache.get(key)
    if count is None:
        cache.set(key, 1, timeout=window_seconds)
        return False
    if count >= limit:
        return True
    try:
        cache.incr(key)
    except ValueError:
        # Key expired between the get() and incr() calls above; start over.
        cache.set(key, 1, timeout=window_seconds)
    return False
