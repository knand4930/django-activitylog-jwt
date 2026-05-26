"""Database router that directs activity log queries to the configured backend."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_ACTIVITYLOG_MODELS = frozenset(
    {
        "crudevent",
        "loginevent",
        "requestevent",
        "corsevent",
        "systemevent",
        "databaseconfig",
        "retentionpolicy",
    }
)

_ROUTE_EVENT_MAP = {
    "crud": {"crudevent"},
    "auth": {"loginevent"},
    "request": {"requestevent"},
    "cors": {"corsevent"},
    "system": {"systemevent"},
    "all": _ACTIVITYLOG_MODELS,
    "analytics": {"requestevent", "crudevent"},
}


class ActivityLogDatabaseRouter:
    """Route activitylog model reads/writes to the configured database.

    Falls back to Django's default DB when no matching active config exists.
    Config-management models (DatabaseConfig, RetentionPolicy) always use
    the default DB to avoid a bootstrap circular dependency.
    """

    _CONFIG_MODELS = frozenset({"databaseconfig", "retentionpolicy"})

    def _alias_for_model(self, model: type, tenant_id: str | None = None) -> str | None:
        """Return the best matching database alias for ``model``, or None."""
        label = model._meta.app_label
        name = model._meta.model_name

        if label != "activitylog":
            return None
        if name in self._CONFIG_MODELS:
            return None  # always use default DB for config tables

        try:
            from activitylog.models import DatabaseConfig
            from activitylog.routing.registry import ensure_config_registered

            qs = DatabaseConfig.objects.filter(is_active=True, is_healthy__in=[True, None])
            if tenant_id:
                qs = qs.filter(tenant_id=tenant_id)

            for cfg in qs.order_by("-is_primary"):
                allowed = _ROUTE_EVENT_MAP.get(cfg.route_for, set())
                if name in allowed:
                    return ensure_config_registered(cfg)
        except Exception as exc:
            logger.debug("ActivityLogRouter: config lookup failed: %s", exc)

        return None

    def db_for_read(self, model: type, **hints: object) -> str | None:
        return self._alias_for_model(model)

    def db_for_write(self, model: type, **hints: object) -> str | None:
        return self._alias_for_model(model)

    def allow_relation(self, obj1: object, obj2: object, **hints: object) -> bool | None:
        return True

    def allow_migrate(
        self,
        db: str,
        app_label: str,
        model_name: str | None = None,
        **hints: object,
    ) -> bool | None:
        if app_label == "activitylog":
            return db == "default"
        return None
