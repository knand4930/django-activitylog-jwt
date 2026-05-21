"""Dynamic database connection registry for multi-database support."""

from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING, Dict, FrozenSet, Optional

if TYPE_CHECKING:
    from activitylog.models import DatabaseConfig

logger = logging.getLogger(__name__)

_lock = threading.RLock()
_registered_aliases: set = set()


def register_database(alias: str, config: Dict[str, object]) -> bool:
    """Register a dynamic database alias in Django's connection handler.

    :param alias: A unique alias string (e.g. ``"activitylog_clickhouse"``).
    :param config: A Django DATABASES-compatible dict.
    :returns: True if newly registered, False if already exists.
    """
    from django.conf import settings
    from django.db import connections

    with _lock:
        if alias in connections.databases:
            return False

        databases = settings.DATABASES.copy()
        databases[alias] = config
        settings.DATABASES = databases
        _registered_aliases.add(alias)
        logger.info("ActivityLog: registered database alias '%s'", alias)
        return True


def unregister_database(alias: str) -> None:
    """Close and remove a dynamic database alias."""
    from django.conf import settings
    from django.db import connections

    with _lock:
        if alias not in _registered_aliases:
            return
        try:
            connections[alias].close()
        except Exception:
            pass
        databases = settings.DATABASES.copy()
        databases.pop(alias, None)
        settings.DATABASES = databases
        _registered_aliases.discard(alias)
        logger.info("ActivityLog: unregistered database alias '%s'", alias)


def get_registered_aliases() -> FrozenSet[str]:
    return frozenset(_registered_aliases)


def alias_for_config(config_id: str) -> str:
    return f"activitylog_{config_id}"


def ensure_config_registered(db_config: "DatabaseConfig") -> Optional[str]:
    """Given a DatabaseConfig ORM object, ensure it is registered and return its alias."""
    from django.db import connections

    alias = alias_for_config(str(db_config.id))

    if alias not in connections.databases:
        django_cfg = db_config.get_django_db_config()
        register_database(alias, django_cfg)

    return alias
