import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def clear_throttle_cache():
    # DRF throttle history lives in the cache; reset it so tests that log in
    # repeatedly don't trip the login rate limit across test boundaries.
    cache.clear()
    yield
    cache.clear()
