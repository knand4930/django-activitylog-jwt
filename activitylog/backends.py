"""Pluggable logging backends.

Each backend implements four methods:  crud / login / request / cors.
Select the backend in settings via:

    DJANGO_ACTIVITY_LOG_LOGGING_BACKEND = "activitylog.backends.AsyncBackend"

Available backends
------------------
ModelBackend     — synchronous Django ORM writes (default)
AsyncBackend     — dispatches writes to Celery tasks; sync fallback if Celery absent
MultiBackend     — fan-out to multiple backends simultaneously
ClickHouseBackend — writes to ClickHouse via clickhouse-driver (optional dep)
MongoBackend     — writes to MongoDB via pymongo (optional dep)
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

class BaseBackend:
    """Interface that all backends must implement."""

    def crud(self, data: dict[str, Any]) -> Any:
        raise NotImplementedError

    def login(self, data: dict[str, Any]) -> Any:
        raise NotImplementedError

    def request(self, data: dict[str, Any]) -> Any:
        raise NotImplementedError

    def cors(self, data: dict[str, Any]) -> Any:
        raise NotImplementedError

    def system(self, data: dict[str, Any]) -> Any:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Synchronous ORM backend (original behaviour)
# ---------------------------------------------------------------------------

class ModelBackend(BaseBackend):
    """Write directly to the database using Django ORM (synchronous)."""

    def _stamp(self, obj) -> None:
        obj.integrity_hash = obj.compute_integrity_hash()
        obj.save(update_fields=["integrity_hash"])

    def crud(self, data: dict[str, Any]):
        from activitylog.models import CRUDEvent
        obj = CRUDEvent.objects.create(**data)
        self._stamp(obj)
        return obj

    def login(self, data: dict[str, Any]):
        from activitylog.models import LoginEvent
        obj = LoginEvent.objects.create(**data)
        self._stamp(obj)
        return obj

    def request(self, data: dict[str, Any]):
        from activitylog.models import RequestEvent
        obj = RequestEvent.objects.create(**data)
        self._stamp(obj)
        return obj

    def cors(self, data: dict[str, Any]):
        from activitylog.models import CorsEvent
        obj = CorsEvent.objects.create(**data)
        self._stamp(obj)
        return obj

    def system(self, data: dict[str, Any]):
        from activitylog.models import SystemEvent
        obj = SystemEvent.objects.create(**data)
        self._stamp(obj)
        return obj


# ---------------------------------------------------------------------------
# Async backend (Celery tasks with sync fallback)
# ---------------------------------------------------------------------------

class AsyncBackend(BaseBackend):
    """Dispatch writes to Celery tasks.  Falls back to synchronous on missing broker."""

    def _dispatch(self, event_type: str, data: dict[str, Any]) -> None:
        from activitylog.tasks.log_tasks import dispatch_log_task
        dispatch_log_task(event_type, data)

    def crud(self, data: dict[str, Any]) -> None:
        self._dispatch("crud", data)

    def login(self, data: dict[str, Any]) -> None:
        self._dispatch("login", data)

    def request(self, data: dict[str, Any]) -> None:
        self._dispatch("request", data)

    def cors(self, data: dict[str, Any]) -> None:
        self._dispatch("cors", data)

    def system(self, data: dict[str, Any]) -> None:
        self._dispatch("system", data)


# ---------------------------------------------------------------------------
# Multi-backend fan-out
# ---------------------------------------------------------------------------

class MultiBackend(BaseBackend):
    """Write to multiple backends simultaneously.

    Configure in settings::

        DJANGO_ACTIVITY_LOG_MULTI_BACKENDS = [
            "activitylog.backends.ModelBackend",
            "activitylog.backends.ClickHouseBackend",
        ]
    """

    def __init__(self) -> None:
        from django.conf import settings
        from django.utils.module_loading import import_string

        backend_paths: list[str] = getattr(
            settings, "DJANGO_ACTIVITY_LOG_MULTI_BACKENDS", []
        )
        self._backends: list[BaseBackend] = [import_string(p)() for p in backend_paths]

    def _fan_out(self, method: str, data: dict[str, Any]) -> None:
        for backend in self._backends:
            try:
                getattr(backend, method)(data)
            except Exception as exc:
                logger.exception("MultiBackend '%s' failed for %s: %s",
                                 type(backend).__name__, method, exc)

    def crud(self, data):
        self._fan_out("crud", data)

    def login(self, data):
        self._fan_out("login", data)

    def request(self, data):
        self._fan_out("request", data)

    def cors(self, data):
        self._fan_out("cors", data)

    def system(self, data):
        self._fan_out("system", data)


# ---------------------------------------------------------------------------
# ClickHouse backend
# ---------------------------------------------------------------------------

class ClickHouseBackend(BaseBackend):
    """Write activity log events directly to ClickHouse.

    Requires ``clickhouse-driver``::

        pip install clickhouse-driver

    Configure in settings::

        ACTIVITYLOG_CLICKHOUSE = {
            "host": "localhost",
            "port": 9000,
            "database": "activitylog",
            "user": "default",
            "password": "",
            "settings": {"use_numpy": False},
        }
    """

    _CLIENT = None
    _TABLE_PREFIX = "al"

    def _get_client(self):
        if self._CLIENT is None:
            from django.conf import settings
            try:
                from clickhouse_driver import Client
            except ImportError as exc:
                raise RuntimeError(
                    "clickhouse-driver is required for ClickHouseBackend. "
                    "Install it with: pip install clickhouse-driver"
                ) from exc

            cfg = getattr(settings, "ACTIVITYLOG_CLICKHOUSE", {})
            self.__class__._CLIENT = Client(
                host=cfg.get("host", "localhost"),
                port=cfg.get("port", 9000),
                database=cfg.get("database", "activitylog"),
                user=cfg.get("user", "default"),
                password=cfg.get("password", ""),
                settings=cfg.get("settings", {}),
            )
        return self._CLIENT

    def _insert(self, table: str, data: dict[str, Any]) -> None:
        client = self._get_client()
        clean = {k: (str(v) if not isinstance(v, (int, float, str, type(None))) else v)
                 for k, v in data.items()}
        columns = list(clean.keys())
        values = [list(clean.values())]
        client.execute(
            f"INSERT INTO {self._TABLE_PREFIX}_{table} ({', '.join(columns)}) VALUES",
            values,
        )

    def crud(self, data):
        self._insert("crud_events", data)

    def login(self, data):
        self._insert("login_events", data)

    def request(self, data):
        self._insert("request_events", data)

    def cors(self, data):
        self._insert("cors_events", data)

    def system(self, data):
        self._insert("system_events", data)


# ---------------------------------------------------------------------------
# MongoDB backend
# ---------------------------------------------------------------------------

class MongoBackend(BaseBackend):
    """Write activity log events to MongoDB.

    Requires ``pymongo``::

        pip install pymongo

    Configure in settings::

        ACTIVITYLOG_MONGODB = {
            "uri": "mongodb://localhost:27017",
            "database": "activitylog",
        }
    """

    _DB = None

    def _get_db(self):
        if self._DB is None:
            from django.conf import settings
            try:
                import pymongo
            except ImportError as exc:
                raise RuntimeError(
                    "pymongo is required for MongoBackend. "
                    "Install it with: pip install pymongo"
                ) from exc

            cfg = getattr(settings, "ACTIVITYLOG_MONGODB", {})
            client = pymongo.MongoClient(cfg.get("uri", "mongodb://localhost:27017"))
            self.__class__._DB = client[cfg.get("database", "activitylog")]
        return self._DB

    def _insert(self, collection: str, data: dict[str, Any]) -> None:
        db = self._get_db()
        doc = {k: (str(v) if not isinstance(v, (int, float, str, bool, type(None), dict, list)) else v)
               for k, v in data.items()}
        db[collection].insert_one(doc)

    def crud(self, data):
        self._insert("crud_events", data)

    def login(self, data):
        self._insert("login_events", data)

    def request(self, data):
        self._insert("request_events", data)

    def cors(self, data):
        self._insert("cors_events", data)

    def system(self, data):
        self._insert("system_events", data)


# ---------------------------------------------------------------------------
# ScyllaDB / Cassandra backend
# ---------------------------------------------------------------------------

class ScyllaDBBackend(BaseBackend):
    """Write activity log events to ScyllaDB (or Apache Cassandra).

    Requires ``cassandra-driver``::

        pip install cassandra-driver

    Configure in settings::

        ACTIVITYLOG_SCYLLADB = {
            "contact_points": ["localhost"],
            "port": 9042,
            "keyspace": "activitylog",
            "username": None,
            "password": None,
        }
    """

    _SESSION = None

    def _get_session(self):
        if self._SESSION is None:
            from django.conf import settings
            try:
                from cassandra.auth import PlainTextAuthProvider
                from cassandra.cluster import Cluster
            except ImportError as exc:
                raise RuntimeError(
                    "cassandra-driver is required for ScyllaDBBackend. "
                    "Install it with: pip install cassandra-driver"
                ) from exc

            cfg = getattr(settings, "ACTIVITYLOG_SCYLLADB", {})
            auth = None
            if cfg.get("username"):
                auth = PlainTextAuthProvider(cfg["username"], cfg.get("password", ""))
            cluster = Cluster(
                contact_points=cfg.get("contact_points", ["localhost"]),
                port=cfg.get("port", 9042),
                auth_provider=auth,
            )
            session = cluster.connect()
            session.set_keyspace(cfg.get("keyspace", "activitylog"))
            self.__class__._SESSION = session
        return self._SESSION

    def _insert(self, table: str, data: dict[str, Any]) -> None:
        session = self._get_session()
        cols = ", ".join(data.keys())
        placeholders = ", ".join(["%s"] * len(data))
        values = [
            str(v) if not isinstance(v, (int, float, str, bool, type(None))) else v
            for v in data.values()
        ]
        session.execute(f"INSERT INTO {table} ({cols}) VALUES ({placeholders})", values)

    def crud(self, data):
        self._insert("crud_events", data)

    def login(self, data):
        self._insert("login_events", data)

    def request(self, data):
        self._insert("request_events", data)

    def cors(self, data):
        self._insert("cors_events", data)

    def system(self, data):
        self._insert("system_events", data)
