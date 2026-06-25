"""
Custom Django test runner with per-worker Redis isolation.

Django's `--parallel` runner provisions a dedicated Postgres test database per
worker but shares every other backend (Redis cache, channel layers, etc.). Any
test that writes to the cache - especially the common `cache.clear()` in
`setUp`/`tearDown` - can race with sibling workers and wipe their in-flight
state, producing flaky failures that don't reproduce sequentially.

This runner rewrites the LOCATION on every `settings.CACHES` alias inside the
pool initializer so each worker connects to a unique Redis database, then
fires `setting_changed` so Django closes any inherited cache backends and
rebuilds them against the per-worker DB on next access. The isolation covers
both `django.core.cache.cache.*` and direct `django_redis.get_redis_connection`
callers, because the latter resolves through `caches[alias]`.

Redis ships with 16 logical databases (0-15). The app itself defaults to DB 1
(via `REDIS_URL`), so workers start at DB 2 and we support up to 14 parallel
workers before exhausting the namespace.
"""
import re

from django.test.runner import DiscoverRunner, ParallelTestSuite
from django.test.runner import _init_worker as django_init_worker


_WORKER_REDIS_DB_OFFSET = 2
_MAX_REDIS_DB = 15


def _init_worker_with_isolated_cache(counter):
    """Pool initializer: run Django's worker setup, then point Redis at a unique DB."""
    django_init_worker(counter)

    from django.conf import settings
    from django.test import runner as _runner_module
    from django.test.signals import setting_changed

    worker_id = _runner_module._worker_id
    worker_db = _WORKER_REDIS_DB_OFFSET + worker_id - 1

    if worker_db > _MAX_REDIS_DB:
        raise RuntimeError(
            "Parallel worker {worker_id} would need Redis DB {db}, but only DBs "
            "up to {max_db} are available. Reduce --parallel or raise Redis "
            "`databases` config.".format(
                worker_id=worker_id, db=worker_db, max_db=_MAX_REDIS_DB
            )
        )

    for config in settings.CACHES.values():
        location = config.get("LOCATION")
        if isinstance(location, str):
            config["LOCATION"] = re.sub(r"/\d+$", "/{}".format(worker_db), location)

    setting_changed.send(
        sender=None,
        setting="CACHES",
        value=settings.CACHES,
        enter=True,
    )


class _IsolatedCacheParallelSuite(ParallelTestSuite):
    init_worker = _init_worker_with_isolated_cache


class IsolatedCacheTestRunner(DiscoverRunner):
    """Django test runner that gives each parallel worker its own Redis DB."""

    parallel_test_suite = _IsolatedCacheParallelSuite
