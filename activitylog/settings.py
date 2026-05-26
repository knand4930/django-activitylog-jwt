"""Backward-compatible settings shim.

All code should use ``activitylog.conf.activitylog_settings`` directly.
This module exposes the same names that older signal/admin code expected
so that existing user overrides keep working without modification.

No model classes are imported here at module load time — that was a circular
import risk in the original design.
"""

from __future__ import annotations

from typing import Any

from activitylog.conf import activitylog_settings as _s

# ---------------------------------------------------------------------------
# Feature flags
# ---------------------------------------------------------------------------
WATCH_AUTH_EVENTS = _s.WATCH_AUTH_EVENTS
WATCH_MODEL_EVENTS = _s.WATCH_MODEL_EVENTS
WATCH_REQUEST_EVENTS = _s.WATCH_REQUEST_EVENTS
WATCH_CORS_EVENTS = _s.WATCH_CORS_EVENTS

# ---------------------------------------------------------------------------
# Request headers
# ---------------------------------------------------------------------------
REMOTE_ADDR_HEADER = _s.EFFECTIVE_REMOTE_ADDR_HEADER
HTTP_SEC_CH_UA = _s.BROWSER_HEADER
HTTP_SEC_CH_UA_PLATFORM = _s.PLATFORM_HEADER
GNOME_SHELL_SESSION_MODE = _s.OS_HEADER

# ---------------------------------------------------------------------------
# Backend / database
# ---------------------------------------------------------------------------
LOGGING_BACKEND = _s.LOGGING_BACKEND
DATABASE_ALIAS = _s.DATABASE_ALIAS
USER_DB_CONSTRAINT = _s.USER_DB_CONSTRAINT

# ---------------------------------------------------------------------------
# URL / model filtering
# ---------------------------------------------------------------------------
UNREGISTERED_URLS = _s.UNREGISTERED_URLS_ALL
REGISTERED_URLS = _s.REGISTERED_URLS

# UNREGISTERED_CLASSES and REGISTERED_CLASSES are resolved lazily at startup
# (inside apps.py ready()) to avoid circular imports during Django init.

# ---------------------------------------------------------------------------
# Admin display
# ---------------------------------------------------------------------------
ADMIN_SHOW_MODEL_EVENTS = _s.ADMIN_SHOW_MODEL_EVENTS
ADMIN_SHOW_AUTH_EVENTS = _s.ADMIN_SHOW_AUTH_EVENTS
ADMIN_SHOW_REQUEST_EVENTS = _s.ADMIN_SHOW_REQUEST_EVENTS
ADMIN_SHOW_CORS_EVENTS = _s.ADMIN_SHOW_CORS_EVENTS
READONLY_EVENTS = _s.READONLY_EVENTS

# ---------------------------------------------------------------------------
# Admin filter / search config
# ---------------------------------------------------------------------------
CRUD_EVENT_LIST_FILTER = _s.CRUD_EVENT_LIST_FILTER
LOGIN_EVENT_LIST_FILTER = _s.LOGIN_EVENT_LIST_FILTER
REQUEST_EVENT_LIST_FILTER = _s.REQUEST_EVENT_LIST_FILTER
CORS_EVENT_LIST_FILTER = _s.CORS_EVENT_LIST_FILTER

CRUD_EVENT_SEARCH_FIELDS = _s.CRUD_EVENT_SEARCH_FIELDS
LOGIN_EVENT_SEARCH_FIELDS = _s.LOGIN_EVENT_SEARCH_FIELDS
REQUEST_EVENT_SEARCH_FIELDS = _s.REQUEST_EVENT_SEARCH_FIELDS
CORS_EVENT_SEARCH_FIELDS = _s.CORS_EVENT_SEARCH_FIELDS

# ---------------------------------------------------------------------------
# CRUD callbacks / misc
# ---------------------------------------------------------------------------
CRUD_DIFFERENCE_CALLBACKS = _s.CRUD_DIFFERENCE_CALLBACKS
CRUD_EVENT_NO_CHANGED_FIELDS_SKIP = _s.CRUD_EVENT_NO_CHANGED_FIELDS_SKIP
TRUNCATE_TABLE_SQL_STATEMENT = _s.TRUNCATE_TABLE_SQL_STATEMENT

UNREGISTERED_CLASSES: list[type[Any]] = []
REGISTERED_CLASSES: list[type[Any]] = []
