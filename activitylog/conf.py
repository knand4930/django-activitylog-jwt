"""Centralized, lazy configuration for django-activitylog-jwt.

Two ways to configure the package:

**New (preferred) — single dict in settings.py:**

    ACTIVITYLOG = {
        "WATCH_AUTH_EVENTS": True,
        "ASYNC_ENABLED": True,
        ...
    }

**Legacy — individual ``DJANGO_ACTIVITY_LOG_*`` keys (still supported):**

    DJANGO_ACTIVITY_LOG_WATCH_AUTH_EVENTS = True
    DJANGO_ACTIVITY_LOG_ASYNC_ENABLED     = True
    ...

When both are present, the new ``ACTIVITYLOG`` dict takes precedence per key.

Access any setting through the module-level ``activitylog_settings`` singleton:

    from activitylog.conf import activitylog_settings
    if activitylog_settings.ASYNC_ENABLED:
        ...
"""

from __future__ import annotations

import os
from typing import Any

# ---------------------------------------------------------------------------
# Default values for every configurable key
# ---------------------------------------------------------------------------

DEFAULTS: dict[str, Any] = {
    # ------------------------------------------------------------------
    # Feature toggles
    # ------------------------------------------------------------------
    "WATCH_AUTH_EVENTS":    True,
    "WATCH_MODEL_EVENTS":   True,
    "WATCH_REQUEST_EVENTS": True,
    "WATCH_CORS_EVENTS":    True,

    # ------------------------------------------------------------------
    # Async / performance
    # ------------------------------------------------------------------
    "ASYNC_ENABLED": True,
    "LOGGING_BACKEND": "activitylog.backends.AsyncBackend",
    "MULTI_BACKENDS": [],        # list of backend dotted paths (for MultiBackend)

    # ------------------------------------------------------------------
    # Request metadata header names
    # ------------------------------------------------------------------
    # Set to "REMOTE_ADDR" if not behind a proxy; "HTTP_X_FORWARDED_FOR" otherwise.
    "REMOTE_ADDR_HEADER":     "HTTP_X_FORWARDED_FOR",
    "BROWSER_HEADER":         "HTTP_SEC_CH_UA",
    "PLATFORM_HEADER":        "HTTP_SEC_CH_UA_PLATFORM",
    "OS_HEADER":              "GNOME_SHELL_SESSION_MODE",

    # ------------------------------------------------------------------
    # Database
    # ------------------------------------------------------------------
    "DATABASE_ALIAS":          "default",
    "USER_DB_CONSTRAINT":      True,
    "CHECK_IF_REQUEST_USER_EXISTS": True,

    # ------------------------------------------------------------------
    # JWT
    # ------------------------------------------------------------------
    # Prefix used in the Authorization header: "Bearer <token>"
    "JWT_AUTH_HEADER_PREFIX": "Bearer",

    # Primary signing algorithm used when issuing tokens.
    # Accepted values: "HS256", "HS384", "HS512",
    #                  "RS256", "RS384", "RS512",
    #                  "ES256", "ES384", "ES512",
    #                  "PS256", "PS384", "PS512"
    "JWT_ALGORITHM": "HS256",

    # Full list of algorithms accepted during decoding.  Tokens whose
    # header 'alg' is not in this list are rejected.
    "JWT_ALGORITHMS": [
        "HS256", "HS384", "HS512",
        "RS256", "RS384", "RS512",
        "ES256", "ES384", "ES512",
        "PS256", "PS384", "PS512",
    ],

    # Shared secret for HMAC algorithms (HS256/HS384/HS512).
    # None → Django's SECRET_KEY is used automatically.
    "JWT_SECRET_KEY": None,

    # PEM-encoded public key string (or file path) for asymmetric algorithms
    # (RS256, RS384, RS512, ES256, ES384, ES512, PS256/384/512).
    # Required when JWT_VERIFY_SIGNATURE=True and JWT_ALGORITHM is asymmetric.
    "JWT_PUBLIC_KEY": None,

    # Whether to verify JWT signatures during request attribution.
    # False (default) — skip verification; authentication middleware handles it.
    # True — verify using JWT_SECRET_KEY (HMAC) or JWT_PUBLIC_KEY (RSA/EC).
    "JWT_VERIFY_SIGNATURE": False,

    # ------------------------------------------------------------------
    # GeoIP
    # ------------------------------------------------------------------
    # Absolute path to a GeoLite2-City.mmdb file.  None = auto-detect from
    # the package's own ``local/`` directory.
    "GEOIP_PATH": None,

    # ------------------------------------------------------------------
    # Security / integrity
    # ------------------------------------------------------------------
    "READONLY_EVENTS":         False,
    "PROPAGATE_EXCEPTIONS":    False,

    # ------------------------------------------------------------------
    # URL filtering (supports regex strings)
    # ------------------------------------------------------------------
    "UNREGISTERED_URLS": [r"^/admin/", r"^/static/", r"^/favicon\.ico$"],
    "UNREGISTERED_URLS_EXTRA": [],
    "REGISTERED_URLS":   [],    # if non-empty, ONLY these URLs are logged

    # ------------------------------------------------------------------
    # Model filtering (dotted strings or class references)
    # ------------------------------------------------------------------
    # These are merged with the built-in exclusion list at startup.
    "UNREGISTERED_CLASSES_EXTRA": [],
    "REGISTERED_CLASSES":         [],   # if non-empty, ONLY these models are logged

    # ------------------------------------------------------------------
    # CRUD callbacks
    # ------------------------------------------------------------------
    "CRUD_DIFFERENCE_CALLBACKS":         [],
    "CRUD_EVENT_NO_CHANGED_FIELDS_SKIP": False,

    # ------------------------------------------------------------------
    # Retention
    # ------------------------------------------------------------------
    "DEFAULT_RETENTION_DAYS": None,     # int or None (policy-driven)

    # ------------------------------------------------------------------
    # Real-time streaming
    # ------------------------------------------------------------------
    "REALTIME_ENABLED": False,

    # ------------------------------------------------------------------
    # Admin UI
    # ------------------------------------------------------------------
    "ADMIN_SHOW_MODEL_EVENTS":   True,
    "ADMIN_SHOW_AUTH_EVENTS":    True,
    "ADMIN_SHOW_REQUEST_EVENTS": True,
    "ADMIN_SHOW_CORS_EVENTS":    True,

    # ------------------------------------------------------------------
    # Admin filter / search field lists
    # ------------------------------------------------------------------
    "CRUD_EVENT_LIST_FILTER":    ["event_type", "content_type", "user", "datetime"],
    "LOGIN_EVENT_LIST_FILTER":   ["login_type", "user", "datetime"],
    "REQUEST_EVENT_LIST_FILTER": ["method", "user", "datetime", "response_status"],
    "CORS_EVENT_LIST_FILTER":    ["method", "user", "datetime"],

    "CRUD_EVENT_SEARCH_FIELDS":    ["=object_id", "object_json_repr"],
    "LOGIN_EVENT_SEARCH_FIELDS":   ["=remote_ip", "username"],
    "REQUEST_EVENT_SEARCH_FIELDS": ["=remote_ip", "user__username", "url", "query_string"],
    "CORS_EVENT_SEARCH_FIELDS":    ["=remote_ip", "user__username", "url", "query_string"],

    # ------------------------------------------------------------------
    # Table purge SQL (optional performance optimisation)
    # ------------------------------------------------------------------
    # Example: 'TRUNCATE TABLE "{db_table}"'
    "TRUNCATE_TABLE_SQL_STATEMENT": "",

    # ------------------------------------------------------------------
    # Response metrics tracking (middleware back-fill)
    # ------------------------------------------------------------------
    "TRACK_RESPONSE_METRICS": True,
}

# Map old-style ``DJANGO_ACTIVITY_LOG_*`` keys → new-style keys
_LEGACY_MAP: dict[str, str] = {
    "DJANGO_ACTIVITY_LOG_WATCH_AUTH_EVENTS":         "WATCH_AUTH_EVENTS",
    "DJANGO_ACTIVITY_LOG_WATCH_MODEL_EVENTS":        "WATCH_MODEL_EVENTS",
    "DJANGO_ACTIVITY_LOG_WATCH_REQUEST_EVENTS":      "WATCH_REQUEST_EVENTS",
    "DJANGO_ACTIVITY_LOG_WATCH_CORS_EVENTS":         "WATCH_CORS_EVENTS",
    "DJANGO_ACTIVITY_LOG_LOGGING_BACKEND":           "LOGGING_BACKEND",
    "DJANGO_ACTIVITY_LOG_ASYNC_ENABLED":             "ASYNC_ENABLED",
    "DJANGO_ACTIVITY_LOG_REMOTE_ADDR_HEADER":        "REMOTE_ADDR_HEADER",
    "DJANGO_ACTIVITY_LOG_BROWSER":                   "BROWSER_HEADER",
    "DJANGO_ACTIVITY_LOG_PLATFORM":                  "PLATFORM_HEADER",
    "DJANGO_ACTIVITY_LOG_OPERATING_SYSTEM":          "OS_HEADER",
    "DJANGO_ACTIVITY_LOG_DATABASE_ALIAS":            "DATABASE_ALIAS",
    "DJANGO_ACTIVITY_LOG_USER_DB_CONSTRAINT":        "USER_DB_CONSTRAINT",
    "DJANGO_ACTIVITY_LOG_CHECK_IF_REQUEST_USER_EXISTS": "CHECK_IF_REQUEST_USER_EXISTS",
    "DJANGO_ACTIVITY_LOG_GEOIP_PATH":                "GEOIP_PATH",
    "DJANGO_ACTIVITY_LOG_READONLY_EVENTS":           "READONLY_EVENTS",
    "DJANGO_ACTIVITY_LOG_PROPAGATE_EXCEPTIONS":      "PROPAGATE_EXCEPTIONS",
    "DJANGO_ACTIVITY_LOG_UNREGISTERED_URLS_DEFAULT": "UNREGISTERED_URLS",
    "DJANGO_ACTIVITY_LOG_UNREGISTERED_URLS_EXTRA":   "UNREGISTERED_URLS_EXTRA",
    "DJANGO_ACTIVITY_LOG_REGISTERED_URLS":           "REGISTERED_URLS",
    "DJANGO_ACTIVITY_LOG_UNREGISTERED_CLASSES_EXTRA": "UNREGISTERED_CLASSES_EXTRA",
    "DJANGO_ACTIVITY_LOG_REGISTERED_CLASSES":        "REGISTERED_CLASSES",
    "DJANGO_ACTIVITY_LOG_CRUD_DIFFERENCE_CALLBACKS": "CRUD_DIFFERENCE_CALLBACKS",
    "DJANGO_ACTIVITY_LOG_CRUD_EVENT_NO_CHANGED_FIELDS_SKIP": "CRUD_EVENT_NO_CHANGED_FIELDS_SKIP",
    "DJANGO_ACTIVITY_LOG_ADMIN_SHOW_MODEL_EVENTS":   "ADMIN_SHOW_MODEL_EVENTS",
    "DJANGO_ACTIVITY_LOG_ADMIN_SHOW_AUTH_EVENTS":    "ADMIN_SHOW_AUTH_EVENTS",
    "DJANGO_ACTIVITY_LOG_ADMIN_SHOW_REQUEST_EVENTS": "ADMIN_SHOW_REQUEST_EVENTS",
    "DJANGO_ACTIVITY_LOG_ADMIN_SHOW_CORS_EVENTS":    "ADMIN_SHOW_CORS_EVENTS",
    "DJANGO_ACTIVITY_LOG_CRUD_EVENT_LIST_FILTER":    "CRUD_EVENT_LIST_FILTER",
    "DJANGO_ACTIVITY_LOG_LOGIN_EVENT_LIST_FILTER":   "LOGIN_EVENT_LIST_FILTER",
    "DJANGO_ACTIVITY_LOG_REQUEST_EVENT_LIST_FILTER": "REQUEST_EVENT_LIST_FILTER",
    "DJANGO_ACTIVITY_LOG_CORS_EVENT_LIST_FILTER":    "CORS_EVENT_LIST_FILTER",
    "DJANGO_ACTIVITY_LOG_CRUD_EVENT_SEARCH_FIELDS":  "CRUD_EVENT_SEARCH_FIELDS",
    "DJANGO_ACTIVITY_LOG_LOGIN_EVENT_SEARCH_FIELDS": "LOGIN_EVENT_SEARCH_FIELDS",
    "DJANGO_ACTIVITY_LOG_REQUEST_EVENT_SEARCH_FIELDS": "REQUEST_EVENT_SEARCH_FIELDS",
    "DJANGO_ACTIVITY_LOG_CORS_EVENT_SEARCH_FIELDS":  "CORS_EVENT_SEARCH_FIELDS",
    "DJANGO_ACTIVITY_LOG_TRUNCATE_TABLE_SQL_STATEMENT": "TRUNCATE_TABLE_SQL_STATEMENT",
    "DJANGO_ACTIVITY_LOG_PRIMARY_KEY":               None,  # handled separately
    "ACTIVITYLOG_REALTIME_ENABLED":                  "REALTIME_ENABLED",
}


class _LazySettings:
    """Lazy proxy that merges Django settings into a single namespace.

    Precedence (highest first):
    1. ``settings.ACTIVITYLOG`` dict key
    2. Legacy ``settings.DJANGO_ACTIVITY_LOG_*`` key
    3. Package default from ``DEFAULTS``
    """

    _cache: dict[str, Any]
    _resolved: bool

    def __init__(self) -> None:
        object.__setattr__(self, "_cache", {})
        object.__setattr__(self, "_resolved", False)

    def _resolve(self) -> None:
        from django.conf import settings as dj_settings

        cache: dict[str, Any] = dict(DEFAULTS)

        # 1. Apply legacy DJANGO_ACTIVITY_LOG_* keys first (lower priority)
        for legacy_key, new_key in _LEGACY_MAP.items():
            if new_key is None:
                continue
            value = getattr(dj_settings, legacy_key, _MISSING)
            if value is not _MISSING:
                cache[new_key] = value

        # 2. Apply new ACTIVITYLOG dict (higher priority, per key)
        activitylog_dict = getattr(dj_settings, "ACTIVITYLOG", {})
        for key, value in activitylog_dict.items():
            cache[key] = value

        # 3. Resolve GEOIP_PATH default
        if cache["GEOIP_PATH"] is None:
            cache["GEOIP_PATH"] = os.path.join(
                os.path.dirname(__file__), "local", "GeoLite2-City.mmdb"
            )

        # 4. Merge URL lists
        unregistered_urls = list(cache["UNREGISTERED_URLS"])
        unregistered_urls.extend(cache["UNREGISTERED_URLS_EXTRA"])
        cache["_UNREGISTERED_URLS_MERGED"] = unregistered_urls

        object.__setattr__(self, "_cache", cache)
        object.__setattr__(self, "_resolved", True)

    def __getattr__(self, name: str) -> Any:
        if not object.__getattribute__(self, "_resolved"):
            self._resolve()
        cache = object.__getattribute__(self, "_cache")
        if name in cache:
            return cache[name]
        raise AttributeError(f"activitylog_settings has no attribute '{name}'")

    def reload(self) -> None:
        """Force re-read of Django settings (useful in tests)."""
        object.__setattr__(self, "_resolved", False)
        object.__setattr__(self, "_cache", {})

    def get(self, name: str, default: Any = None) -> Any:
        try:
            return getattr(self, name)
        except AttributeError:
            return default

    @property
    def EFFECTIVE_REMOTE_ADDR_HEADER(self) -> str:
        """The real header name after stripping proxy chaining."""
        raw = self.REMOTE_ADDR_HEADER
        if raw and "," in raw:
            return raw.split(",")[0].strip()
        return raw or "REMOTE_ADDR"

    @property
    def UNREGISTERED_URLS_ALL(self) -> list[str]:
        """Merged unregistered URL list."""
        if not object.__getattribute__(self, "_resolved"):
            self._resolve()
        return object.__getattribute__(self, "_cache").get("_UNREGISTERED_URLS_MERGED", [])


_MISSING = object()

# Module-level singleton — import this everywhere
activitylog_settings = _LazySettings()
