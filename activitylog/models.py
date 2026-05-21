"""Activity log models — compatible with Django 4.2 – 6.x and Python 3.10 – 3.13+."""

from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any, Dict

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


def _compute_hash(data: dict) -> str:
    payload = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()


class BaseEvent(models.Model):
    """Abstract base for all activity log events."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    browser = models.TextField(null=True, blank=True, verbose_name=_("Browser"))
    platform = models.TextField(null=True, blank=True, verbose_name=_("Platform"))
    operating_system = models.TextField(null=True, blank=True, verbose_name=_("Operating system"))
    user_agent = models.TextField(null=True, blank=True, verbose_name=_("User agent"))

    latitude = models.CharField(max_length=50, null=True, blank=True, verbose_name=_("Latitude"))
    longitude = models.CharField(max_length=50, null=True, blank=True, verbose_name=_("Longitude"))
    city = models.CharField(max_length=255, null=True, blank=True, verbose_name=_("City"))
    country = models.CharField(max_length=255, null=True, blank=True, verbose_name=_("Country"))
    country_code = models.CharField(max_length=10, null=True, blank=True, verbose_name=_("Country code"))

    remote_ip = models.CharField(max_length=50, null=True, blank=True, db_index=True, verbose_name=_("Remote IP"))

    integrity_hash = models.CharField(max_length=64, null=True, blank=True, editable=False,
                                      verbose_name=_("Integrity hash"))
    extra_data = models.JSONField(null=True, blank=True, verbose_name=_("Extra data"))
    datetime = models.DateTimeField(default=timezone.now, db_index=True, verbose_name=_("Date time"))

    class Meta:
        abstract = True

    def _hash_fields(self) -> Dict[str, Any]:
        raise NotImplementedError

    def compute_integrity_hash(self) -> str:
        return _compute_hash(self._hash_fields())

    def verify_integrity(self) -> bool:
        return self.integrity_hash == self.compute_integrity_hash()


# ---------------------------------------------------------------------------
# CRUD Events
# ---------------------------------------------------------------------------

class CRUDEvent(BaseEvent):
    CREATE = 1
    UPDATE = 2
    DELETE = 3
    M2M_CHANGE = 4
    M2M_CHANGE_REV = 5
    M2M_ADD = 6
    M2M_ADD_REV = 7
    M2M_REMOVE = 8
    M2M_REMOVE_REV = 9
    M2M_CLEAR = 10
    M2M_CLEAR_REV = 11

    TYPES = (
        (CREATE, _("Create")),
        (UPDATE, _("Update")),
        (DELETE, _("Delete")),
        (M2M_CHANGE, _("Many-to-Many Change")),
        (M2M_CHANGE_REV, _("Reverse Many-to-Many Change")),
        (M2M_ADD, _("Many-to-Many Add")),
        (M2M_ADD_REV, _("Reverse Many-to-Many Add")),
        (M2M_REMOVE, _("Many-to-Many Remove")),
        (M2M_REMOVE_REV, _("Reverse Many-to-Many Remove")),
        (M2M_CLEAR, _("Many-to-Many Clear")),
        (M2M_CLEAR_REV, _("Reverse Many-to-Many Clear")),
    )

    event_type = models.SmallIntegerField(choices=TYPES, db_index=True, verbose_name=_("Event type"))
    object_id = models.CharField(max_length=255, db_index=True, verbose_name=_("Object ID"))
    content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, db_constraint=False, verbose_name=_("Content type")
    )
    object_repr = models.TextField(null=True, blank=True, verbose_name=_("Object representation"))
    object_json_repr = models.TextField(null=True, blank=True, verbose_name=_("Object JSON representation"))
    changed_fields = models.TextField(null=True, blank=True, verbose_name=_("Changed fields"))

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, db_constraint=False, verbose_name=_("User"),
    )
    user_pk_as_string = models.CharField(max_length=255, null=True, blank=True,
                                         verbose_name=_("User PK as string"))

    def is_create(self):
        return self.event_type == self.CREATE

    def is_update(self):
        return self.event_type == self.UPDATE

    def is_delete(self):
        return self.event_type == self.DELETE

    def _hash_fields(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "event_type": self.event_type,
            "object_id": str(self.object_id),
            "content_type_id": self.content_type_id,
            "user_pk": self.user_pk_as_string,
            "datetime": str(self.datetime),
            "remote_ip": self.remote_ip,
        }

    class Meta:
        verbose_name = _("CRUD event")
        verbose_name_plural = _("CRUD events")
        ordering = ["-datetime"]
        indexes = [
            models.Index(fields=["object_id", "content_type"]),
            models.Index(fields=["user", "datetime"]),
            models.Index(fields=["event_type", "datetime"]),
            models.Index(fields=["remote_ip", "datetime"]),
        ]


# ---------------------------------------------------------------------------
# Login Events
# ---------------------------------------------------------------------------

class LoginEvent(BaseEvent):
    LOGIN = 0
    LOGOUT = 1
    FAILED = 2
    TOKEN_REFRESH = 3
    PASSWORD_CHANGE = 4

    TYPES = (
        (LOGIN, _("Login")),
        (LOGOUT, _("Logout")),
        (FAILED, _("Failed login")),
        (TOKEN_REFRESH, _("Token refresh")),
        (PASSWORD_CHANGE, _("Password change")),
    )

    login_type = models.SmallIntegerField(choices=TYPES, db_index=True, verbose_name=_("Event type"))
    username = models.CharField(max_length=255, null=True, blank=True, db_index=True, verbose_name=_("Username"))
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, db_constraint=False, verbose_name=_("User"),
    )
    session_key = models.CharField(max_length=255, null=True, blank=True, verbose_name=_("Session key"))

    def _hash_fields(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "login_type": self.login_type,
            "username": self.username,
            "user_id": str(self.user_id) if self.user_id else None,
            "datetime": str(self.datetime),
            "remote_ip": self.remote_ip,
        }

    class Meta:
        verbose_name = _("Login event")
        verbose_name_plural = _("Login events")
        ordering = ["-datetime"]
        indexes = [
            models.Index(fields=["username", "datetime"]),
            models.Index(fields=["login_type", "datetime"]),
            models.Index(fields=["user", "datetime"]),
        ]


# ---------------------------------------------------------------------------
# Request Events
# ---------------------------------------------------------------------------

class RequestEvent(BaseEvent):
    url = models.CharField(max_length=2048, db_index=True, verbose_name=_("URL"))
    method = models.CharField(max_length=20, db_index=True, verbose_name=_("Method"))
    query_string = models.TextField(null=True, blank=True, verbose_name=_("Query string"))
    response_status = models.SmallIntegerField(null=True, blank=True, db_index=True,
                                               verbose_name=_("Response status"))
    response_time_ms = models.FloatField(null=True, blank=True, verbose_name=_("Response time (ms)"))
    request_body_size = models.BigIntegerField(null=True, blank=True, verbose_name=_("Request body size"))
    response_body_size = models.BigIntegerField(null=True, blank=True, verbose_name=_("Response body size"))

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, db_constraint=False, verbose_name=_("User"),
    )

    def _hash_fields(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "url": self.url,
            "method": self.method,
            "user_id": str(self.user_id) if self.user_id else None,
            "datetime": str(self.datetime),
            "remote_ip": self.remote_ip,
        }

    class Meta:
        verbose_name = _("Request event")
        verbose_name_plural = _("Request events")
        ordering = ["-datetime"]
        indexes = [
            models.Index(fields=["method", "datetime"]),
            models.Index(fields=["response_status", "datetime"]),
            models.Index(fields=["user", "datetime"]),
            models.Index(fields=["url", "datetime"]),
        ]


# ---------------------------------------------------------------------------
# CORS Events
# ---------------------------------------------------------------------------

class CorsEvent(BaseEvent):
    url = models.CharField(max_length=2048, null=True, blank=True, db_index=True, verbose_name=_("URL"))
    method = models.CharField(max_length=20, null=True, blank=True, db_index=True, verbose_name=_("Method"))
    query_string = models.TextField(null=True, blank=True, verbose_name=_("Query string"))
    origin = models.CharField(max_length=512, null=True, blank=True, db_index=True, verbose_name=_("Origin"))
    allowed = models.BooleanField(null=True, blank=True, verbose_name=_("Allowed"))

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, db_constraint=False, verbose_name=_("User"),
    )

    def _hash_fields(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "url": self.url,
            "method": self.method,
            "origin": self.origin,
            "datetime": str(self.datetime),
            "remote_ip": self.remote_ip,
        }

    class Meta:
        verbose_name = _("CORS event")
        verbose_name_plural = _("CORS events")
        ordering = ["-datetime"]
        indexes = [
            models.Index(fields=["origin", "datetime"]),
            models.Index(fields=["allowed", "datetime"]),
        ]


# ---------------------------------------------------------------------------
# System Events
# ---------------------------------------------------------------------------

class SystemEvent(BaseEvent):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

    SEVERITY_CHOICES = (
        (INFO, _("Info")),
        (WARNING, _("Warning")),
        (ERROR, _("Error")),
        (CRITICAL, _("Critical")),
    )

    CATEGORY_SERVER = "server"
    CATEGORY_SECURITY = "security"
    CATEGORY_DATABASE = "database"
    CATEGORY_CELERY = "celery"
    CATEGORY_CUSTOM = "custom"

    CATEGORY_CHOICES = (
        (CATEGORY_SERVER, _("Server")),
        (CATEGORY_SECURITY, _("Security")),
        (CATEGORY_DATABASE, _("Database")),
        (CATEGORY_CELERY, _("Celery")),
        (CATEGORY_CUSTOM, _("Custom")),
    )

    event_name = models.CharField(max_length=255, db_index=True, verbose_name=_("Event name"))
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default=INFO,
                                db_index=True, verbose_name=_("Severity"))
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default=CATEGORY_CUSTOM,
                                db_index=True, verbose_name=_("Category"))
    message = models.TextField(verbose_name=_("Message"))
    source = models.CharField(max_length=512, null=True, blank=True, verbose_name=_("Source"))
    traceback = models.TextField(null=True, blank=True, verbose_name=_("Traceback"))

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, db_constraint=False, verbose_name=_("User"),
    )

    def _hash_fields(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "event_name": self.event_name,
            "severity": self.severity,
            "category": self.category,
            "message": self.message,
            "datetime": str(self.datetime),
        }

    class Meta:
        verbose_name = _("System event")
        verbose_name_plural = _("System events")
        ordering = ["-datetime"]
        indexes = [
            models.Index(fields=["severity", "datetime"]),
            models.Index(fields=["category", "datetime"]),
            models.Index(fields=["event_name", "datetime"]),
        ]


# ---------------------------------------------------------------------------
# Database Configuration (multi-DB support)
# ---------------------------------------------------------------------------

class DatabaseConfig(models.Model):
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    SQLITE = "sqlite"
    CLICKHOUSE = "clickhouse"
    MONGODB = "mongodb"
    SCYLLADB = "scylladb"

    ENGINE_CHOICES = (
        (POSTGRESQL, _("PostgreSQL")),
        (MYSQL, _("MySQL")),
        (SQLITE, _("SQLite")),
        (CLICKHOUSE, _("ClickHouse")),
        (MONGODB, _("MongoDB")),
        (SCYLLADB, _("ScyllaDB / Cassandra")),
    )

    ROUTE_ALL = "all"
    ROUTE_CRUD = "crud"
    ROUTE_AUTH = "auth"
    ROUTE_REQUEST = "request"
    ROUTE_SYSTEM = "system"
    ROUTE_ANALYTICS = "analytics"

    ROUTE_CHOICES = (
        (ROUTE_ALL, _("All events")),
        (ROUTE_CRUD, _("CRUD events only")),
        (ROUTE_AUTH, _("Auth/login events only")),
        (ROUTE_REQUEST, _("Request events only")),
        (ROUTE_SYSTEM, _("System events only")),
        (ROUTE_ANALYTICS, _("Analytics / high-volume")),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True, verbose_name=_("Name"))
    engine = models.CharField(max_length=50, choices=ENGINE_CHOICES, verbose_name=_("Engine"))

    host = models.CharField(max_length=512, verbose_name=_("Host"))
    port = models.PositiveIntegerField(null=True, blank=True, verbose_name=_("Port"))
    database_name = models.CharField(max_length=255, verbose_name=_("Database name"))
    username = models.CharField(max_length=255, null=True, blank=True, verbose_name=_("Username"))
    # Stored encrypted — see DatabaseConfig.save()
    _password = models.TextField(null=True, blank=True, db_column="password",
                                 verbose_name=_("Password (encrypted)"))

    route_for = models.CharField(max_length=20, choices=ROUTE_CHOICES, default=ROUTE_ALL,
                                 verbose_name=_("Route for"))
    is_primary = models.BooleanField(default=False, verbose_name=_("Is primary"))
    is_active = models.BooleanField(default=True, db_index=True, verbose_name=_("Is active"))
    is_readonly = models.BooleanField(default=False, verbose_name=_("Read only"))

    # Per-tenant isolation
    tenant_id = models.CharField(max_length=255, null=True, blank=True, db_index=True,
                                 verbose_name=_("Tenant ID"))

    # Extra options as JSON (pool_size, ssl_mode, timeout, etc.)
    connection_options = models.JSONField(default=dict, blank=True, verbose_name=_("Connection options"))

    # Health tracking
    last_health_check = models.DateTimeField(null=True, blank=True, verbose_name=_("Last health check"))
    is_healthy = models.BooleanField(null=True, blank=True, verbose_name=_("Is healthy"))
    health_error = models.TextField(null=True, blank=True, verbose_name=_("Health error"))

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Database configuration")
        verbose_name_plural = _("Database configurations")
        ordering = ["-is_primary", "name"]

    def __str__(self):
        return f"{self.name} ({self.engine})"

    @property
    def password(self) -> str | None:
        if not self._password:
            return None
        try:
            from activitylog.security.integrity import decrypt_credential
            return decrypt_credential(self._password)
        except Exception:
            return self._password

    @password.setter
    def password(self, value: str | None) -> None:
        if value is None:
            self._password = None
        else:
            try:
                from activitylog.security.integrity import encrypt_credential
                self._password = encrypt_credential(value)
            except Exception:
                self._password = value

    def get_django_db_config(self) -> Dict[str, Any]:
        """Return a Django DATABASES-compatible dict for this config."""
        engine_map = {
            self.POSTGRESQL: "django.db.backends.postgresql",
            self.MYSQL: "django.db.backends.mysql",
            self.SQLITE: "django.db.backends.sqlite3",
        }
        cfg: dict = {
            "ENGINE": engine_map.get(self.engine, "django.db.backends.postgresql"),
            "NAME": self.database_name,
            "HOST": self.host,
            "USER": self.username or "",
            "PASSWORD": self.password or "",
            "OPTIONS": self.connection_options or {},
        }
        if self.port:
            cfg["PORT"] = str(self.port)
        return cfg


# ---------------------------------------------------------------------------
# Retention Policy
# ---------------------------------------------------------------------------

class RetentionPolicy(models.Model):
    CRUD_EVENTS = "crud"
    LOGIN_EVENTS = "login"
    REQUEST_EVENTS = "request"
    CORS_EVENTS = "cors"
    SYSTEM_EVENTS = "system"
    ALL_EVENTS = "all"

    EVENT_TYPE_CHOICES = (
        (CRUD_EVENTS, _("CRUD events")),
        (LOGIN_EVENTS, _("Login events")),
        (REQUEST_EVENTS, _("Request events")),
        (CORS_EVENTS, _("CORS events")),
        (SYSTEM_EVENTS, _("System events")),
        (ALL_EVENTS, _("All events")),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True, verbose_name=_("Name"))
    event_type = models.CharField(max_length=20, choices=EVENT_TYPE_CHOICES, default=ALL_EVENTS,
                                  verbose_name=_("Event type"))
    retain_days = models.PositiveIntegerField(verbose_name=_("Retain for (days)"))
    is_active = models.BooleanField(default=True, verbose_name=_("Is active"))
    tenant_id = models.CharField(max_length=255, null=True, blank=True, db_index=True,
                                 verbose_name=_("Tenant ID"))
    last_run = models.DateTimeField(null=True, blank=True, verbose_name=_("Last run"))
    records_deleted = models.BigIntegerField(default=0, verbose_name=_("Records deleted (total)"))

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Retention policy")
        verbose_name_plural = _("Retention policies")

    def __str__(self):
        return f"{self.name}: keep {self.event_type} for {self.retain_days}d"
