"""
Test / example settings for django-activitylog-jwt.

This file doubles as a comprehensive reference: every supported option is
shown with its default value and a brief comment explaining what it does.
Copy the ``ACTIVITYLOG`` dict into your own project's settings.py and
remove or override any key you want to change.

Supports: Django 4.x – 6.x  |  Python 3.8 – 3.14+
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Django core
# ---------------------------------------------------------------------------
SECRET_KEY = "django-insecure-test-key-do-not-use-in-production"

DEBUG = True

ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # --- Activity log package ---
    "activitylog",
    # Optional: DRF (required for the REST API endpoints)
    "rest_framework",
]

MIDDLEWARE = [
    # ActivityLog middleware MUST come first so the request object is stored
    # in thread-local storage before any signal fires.
    "activitylog.middleware.middleware.ActivityLogMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "tests.urls"

TEMPLATES: list[dict[str, Any]] = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "tests.wsgi.application"
ASGI_APPLICATION = "tests.asgi.application"

DATABASES: dict[str, dict[str, Any]] = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Django REST Framework
# ---------------------------------------------------------------------------
REST_FRAMEWORK: dict[str, Any] = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        # Uncomment the JWT backend you use:
        # "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
}

# ---------------------------------------------------------------------------
# django-activitylog-jwt configuration
#
# All keys shown here are optional — the package works out-of-the-box with
# zero configuration.  Override only what you need.
# ---------------------------------------------------------------------------
ACTIVITYLOG: dict[str, Any] = {
    # -----------------------------------------------------------------------
    # Feature toggles
    # -----------------------------------------------------------------------
    # Track Django signal-based model Create / Update / Delete events.
    "WATCH_MODEL_EVENTS": True,
    # Track user login / logout / failed-login events.
    "WATCH_AUTH_EVENTS": True,
    # Track every HTTP request (url, method, user, IP, geo, timing).
    "WATCH_REQUEST_EVENTS": True,
    # Track CORS / cross-origin requests (requires X-Frontend-URL header).
    "WATCH_CORS_EVENTS": True,
    # -----------------------------------------------------------------------
    # Performance & async
    # -----------------------------------------------------------------------
    # Use Celery for async log writes (recommended for production).
    # Falls back to synchronous ORM writes when Celery is not configured.
    "ASYNC_ENABLED": True,
    # Backend class used for writing log entries.
    # Options:
    #   "activitylog.backends.AsyncBackend"      — Celery tasks (default)
    #   "activitylog.backends.ModelBackend"       — synchronous ORM
    #   "activitylog.backends.MultiBackend"       — fan-out to multiple backends
    #   "activitylog.backends.ClickHouseBackend"  — ClickHouse (requires clickhouse-driver)
    #   "activitylog.backends.MongoBackend"       — MongoDB (requires pymongo)
    #   "activitylog.backends.ScyllaDBBackend"    — ScyllaDB/Cassandra (requires cassandra-driver)
    "LOGGING_BACKEND": "activitylog.backends.AsyncBackend",
    # Used only when LOGGING_BACKEND = "activitylog.backends.MultiBackend"
    # "MULTI_BACKENDS": [
    #     "activitylog.backends.ModelBackend",
    #     "activitylog.backends.ClickHouseBackend",
    # ],
    # -----------------------------------------------------------------------
    # Request metadata
    # -----------------------------------------------------------------------
    # HTTP header used to extract the real client IP address.
    # Use "REMOTE_ADDR" if your app is not behind a reverse proxy.
    # Use "HTTP_X_FORWARDED_FOR" when behind nginx / AWS ELB / Cloudflare.
    "REMOTE_ADDR_HEADER": "REMOTE_ADDR",
    # Client-hints headers for browser/platform detection.
    "BROWSER_HEADER": "HTTP_SEC_CH_UA",
    "PLATFORM_HEADER": "HTTP_SEC_CH_UA_PLATFORM",
    "OS_HEADER": "GNOME_SHELL_SESSION_MODE",
    # Capture HTTP response status code and timing in RequestEvent.
    # Requires ActivityLogMiddleware to be placed first in MIDDLEWARE.
    "TRACK_RESPONSE_METRICS": True,
    # -----------------------------------------------------------------------
    # JWT integration
    # -----------------------------------------------------------------------
    # Prefix used in the Authorization header ("Bearer <token>").
    # Change to "JWT" if you use the older djangorestframework-jwt library.
    "JWT_AUTH_HEADER_PREFIX": "Bearer",
    # JWT libraries are auto-detected in this priority order:
    #   1. djangorestframework-simplejwt  (recommended, actively maintained)
    #   2. djangorestframework-jwt        (legacy, still supported)
    #   3. PyJWT                          (fallback, read-only decode)
    # Install one of them:
    #   pip install djangorestframework-simplejwt   ← recommended
    #   pip install djangorestframework-jwt         ← legacy
    # No configuration needed — the package detects whichever is installed.
    # Signing algorithm used by your JWT provider.
    # Symmetric:  "HS256" | "HS384" | "HS512"
    # Asymmetric: "RS256" | "RS384" | "RS512"   (RSA, needs JWT_PUBLIC_KEY)
    #             "ES256" | "ES384" | "ES512"   (ECDSA, needs JWT_PUBLIC_KEY)
    #             "PS256" | "PS384" | "PS512"   (RSA-PSS, needs JWT_PUBLIC_KEY)
    "JWT_ALGORITHM": "HS256",
    # Complete list of algorithms accepted when decoding tokens.
    # Tokens whose header 'alg' is not in this list are rejected.
    "JWT_ALGORITHMS": [
        "HS256",
        "HS384",
        "HS512",
        "RS256",
        "RS384",
        "RS512",
        "ES256",
        "ES384",
        "ES512",
        "PS256",
        "PS384",
        "PS512",
    ],
    # Shared secret for HMAC algorithms (HS*).
    # None → Django's SECRET_KEY is used automatically.
    "JWT_SECRET_KEY": None,
    # PEM-encoded public key string or absolute file path for RS*/ES*/PS*
    # algorithms.  Only required when JWT_VERIFY_SIGNATURE = True.
    # Example (inline PEM):  "-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----"
    # Example (file path):   "/etc/ssl/jwt/public.pem"
    "JWT_PUBLIC_KEY": None,
    # Verify JWT signatures during request attribution.
    # False (default) — skip; auth middleware already verified the token.
    # True            — re-verify using JWT_SECRET_KEY (HMAC) or JWT_PUBLIC_KEY (RSA/EC).
    "JWT_VERIFY_SIGNATURE": False,
    # -----------------------------------------------------------------------
    # Database
    # -----------------------------------------------------------------------
    # Django database alias to use for log writes.
    # Change to route activity logs to a dedicated database.
    "DATABASE_ALIAS": "default",
    # Verify that the user still exists in the database before logging.
    "CHECK_IF_REQUEST_USER_EXISTS": True,
    # -----------------------------------------------------------------------
    # GeoIP location lookup
    # -----------------------------------------------------------------------
    # Absolute path to a MaxMind GeoLite2-City.mmdb file.
    # Download free at: https://dev.maxmind.com/geoip/geolite2-free-geolocation-data
    # Leave as None to use the bundled stub (no geo data without the file).
    "GEOIP_PATH": None,
    # -----------------------------------------------------------------------
    # URL filtering
    # -----------------------------------------------------------------------
    # URLs matching these regex patterns are NOT logged (blacklist).
    "UNREGISTERED_URLS": [
        r"^/admin/",
        r"^/static/",
        r"^/favicon\.ico$",
        r"^/health/",
        r"^/metrics/",
    ],
    # Additional URLs to exclude (merged with UNREGISTERED_URLS).
    # Useful to extend without overriding the default list.
    "UNREGISTERED_URLS_EXTRA": [],
    # If non-empty, ONLY these URL patterns are logged (whitelist).
    # Overrides UNREGISTERED_URLS when set.
    "REGISTERED_URLS": [],
    # -----------------------------------------------------------------------
    # Model filtering
    # -----------------------------------------------------------------------
    # Additional model classes (or "app_label.ModelName" strings) to exclude
    # from CRUD event logging.  The package's own models are always excluded.
    "UNREGISTERED_CLASSES_EXTRA": [],
    # If non-empty, ONLY these models are logged (whitelist).
    "REGISTERED_CLASSES": [],
    # -----------------------------------------------------------------------
    # CRUD event options
    # -----------------------------------------------------------------------
    # Skip creating a CRUDEvent when no fields changed during an update.
    "CRUD_EVENT_NO_CHANGED_FIELDS_SKIP": False,
    # Dotted-path callables invoked before each CRUD event is created.
    # Return False from any callback to suppress the event.
    "CRUD_DIFFERENCE_CALLBACKS": [],
    # -----------------------------------------------------------------------
    # Security & integrity
    # -----------------------------------------------------------------------
    # Make all log admin views read-only (no edit/delete through admin).
    "READONLY_EVENTS": False,
    # Re-raise exceptions from signal handlers instead of swallowing them.
    # Keep False in production to avoid breaking requests due to log failures.
    "PROPAGATE_EXCEPTIONS": False,
    # -----------------------------------------------------------------------
    # Real-time streaming (requires Django Channels + channels-redis)
    # -----------------------------------------------------------------------
    # Enable WebSocket and SSE real-time log streaming.
    # Also set CHANNEL_LAYERS in your settings when enabling this.
    "REALTIME_ENABLED": False,
    # -----------------------------------------------------------------------
    # Retention
    # -----------------------------------------------------------------------
    # Global default retention (days) applied when no RetentionPolicy matches.
    # None = no automatic deletion (use RetentionPolicy model for fine control).
    "DEFAULT_RETENTION_DAYS": None,
    # -----------------------------------------------------------------------
    # Admin display toggles
    # -----------------------------------------------------------------------
    "ADMIN_SHOW_MODEL_EVENTS": True,
    "ADMIN_SHOW_AUTH_EVENTS": True,
    "ADMIN_SHOW_REQUEST_EVENTS": True,
    "ADMIN_SHOW_CORS_EVENTS": True,
    # -----------------------------------------------------------------------
    # Table truncation SQL (performance — PostgreSQL example)
    # -----------------------------------------------------------------------
    # When set, this raw SQL is used instead of ORM .delete() for the "Purge"
    # admin action.  Much faster for millions of rows.
    # Example: 'TRUNCATE TABLE "{db_table}" RESTART IDENTITY CASCADE'
    "TRUNCATE_TABLE_SQL_STATEMENT": "",
}

# ---------------------------------------------------------------------------
# Celery (optional — required when ASYNC_ENABLED = True)
# ---------------------------------------------------------------------------
# CELERY_BROKER_URL  = "redis://localhost:6379/0"
# CELERY_RESULT_BACKEND = "redis://localhost:6379/0"
# CELERY_BEAT_SCHEDULE = {
#     **activitylog.settings.CELERY_BEAT_SCHEDULE,   # retention + health checks
# }

# ---------------------------------------------------------------------------
# Django Channels (optional — required when REALTIME_ENABLED = True)
# ---------------------------------------------------------------------------
# CHANNEL_LAYERS = {
#     "default": {
#         "BACKEND": "channels_redis.core.RedisChannelLayer",
#         "CONFIG": {"hosts": [("localhost", 6379)]},
#     }
# }

# ---------------------------------------------------------------------------
# ClickHouse backend (optional — requires clickhouse-driver)
# ---------------------------------------------------------------------------
# ACTIVITYLOG_CLICKHOUSE = {
#     "host": "localhost",
#     "port": 9000,
#     "database": "activitylog",
#     "user": "default",
#     "password": "",
# }

# ---------------------------------------------------------------------------
# MongoDB backend (optional — requires pymongo)
# ---------------------------------------------------------------------------
# ACTIVITYLOG_MONGODB = {
#     "uri": "mongodb://localhost:27017",
#     "database": "activitylog",
# }

# ---------------------------------------------------------------------------
# ScyllaDB / Cassandra backend (optional — requires cassandra-driver)
# ---------------------------------------------------------------------------
# ACTIVITYLOG_SCYLLADB = {
#     "contact_points": ["localhost"],
#     "port": 9042,
#     "keyspace": "activitylog",
# }

# ---------------------------------------------------------------------------
# Multi-database routing (optional)
# ---------------------------------------------------------------------------
# DATABASE_ROUTERS = ["activitylog.routing.routers.ActivityLogDatabaseRouter"]
# DATABASES["logs"] = {
#     "ENGINE": "django.db.backends.postgresql",
#     "NAME": "activitylogs",
#     "HOST": "logs-db.internal",
#     "USER": "loguser",
#     "PASSWORD": "...",
# }
