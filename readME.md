# django-activitylog-jwt

[![PyPI version](https://img.shields.io/pypi/v/django-activitylog-jwt)](https://pypi.org/project/django-activitylog-jwt/)
[![Python](https://img.shields.io/pypi/pyversions/django-activitylog-jwt)](https://pypi.org/project/django-activitylog-jwt/)
[![Django](https://img.shields.io/badge/django-4.2%20%E2%80%93%206.x-green)](https://www.djangoproject.com/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

Production-ready activity logging for Django. Tracks model CRUD events, authentication events, HTTP requests, and CORS requests with SHA-256 tamper-proof integrity hashing, async Celery processing, multi-database routing, DRF REST APIs, real-time WebSocket/SSE streaming, and per-tenant retention policies.

---

## Table of Contents

- [Requirements](#requirements)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Complete Configuration Reference](#complete-configuration-reference)
- [JWT Integration](#jwt-integration)
  - [HS256 (default)](#hs256-default)
  - [RS256 / Asymmetric Algorithms](#rs256--asymmetric-algorithms)
  - [Signature Verification](#signature-verification)
  - [Token Claim Mapping](#token-claim-mapping)
- [Proxy & IP Configuration](#proxy--ip-configuration)
- [GeoIP Setup](#geoip-setup)
- [REST API](#rest-api)
- [CORS Tracking](#cors-tracking)
- [Multi-Database Support](#multi-database-support)
- [Async Processing with Celery](#async-processing-with-celery)
- [Real-Time Streaming](#real-time-streaming)
- [Retention Policies](#retention-policies)
- [Integrity Verification](#integrity-verification)
- [Admin Configuration](#admin-configuration)
- [Permissions (RBAC)](#permissions-rbac)
- [Management Commands](#management-commands)
- [Optional Dependencies](#optional-dependencies)
- [Third-Party Auth Compatibility](#third-party-auth-compatibility)
- [Custom Backends](#custom-backends)
- [Upgrading from v1](#upgrading-from-v1)
- [Development](#development)

---

## Requirements

| Package | Version | Notes |
|---|---|---|
| Python | ≥ 3.10 | 3.10, 3.11, 3.12, 3.13 tested |
| Django | ≥ 4.2 | 4.2 LTS through 6.x |
| djangorestframework | ≥ 3.14 | Required for REST API endpoints |
| geoip2 | ≥ 4.8 | Geo-IP city lookups |

---

## Installation

```bash
pip install django-activitylog-jwt
```

Install with optional feature groups as needed:

```bash
# JWT support (recommended)
pip install "django-activitylog-jwt[jwt]"

# Async Celery processing
pip install "django-activitylog-jwt[celery]"

# API filtering with django-filter
pip install "django-activitylog-jwt[filters]"

# Everything at once
pip install "django-activitylog-jwt[all]"
```

See the [Optional Dependencies](#optional-dependencies) section for the full list.

---

## Quick Start

### 1. Add to `INSTALLED_APPS`

```python
# settings.py
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # ── Activity log ──
    "activitylog",
    # ── Required for REST API endpoints ──
    "rest_framework",
]
```

### 2. Add middleware — must be first

```python
MIDDLEWARE = [
    "activitylog.middleware.middleware.ActivityLogMiddleware",   # ← FIRST
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
```

Placing `ActivityLogMiddleware` first allows it to measure response time and capture status codes for every request.

### 3. Run migrations

```bash
python manage.py migrate activitylog
```

### 4. Mount API URLs (optional)

```python
# urls.py
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/activity/", include("activitylog.api.urls")),   # ← add this
    ...
]
```

### 5. Done

Zero configuration is required. The package logs model changes, auth events, and HTTP requests out of the box with SQLite and synchronous writes. Add `ACTIVITYLOG = {...}` to your settings only when you need to override defaults.

---

## Complete Configuration Reference

All settings live inside a single `ACTIVITYLOG` dict. Every key is optional; the defaults below are used when a key is absent.

```python
# settings.py
ACTIVITYLOG = {

    # ──────────────────────────────────────────────────────────────────────────
    # Feature toggles
    # ──────────────────────────────────────────────────────────────────────────

    # Track Django signal-based model Create / Update / Delete events.
    "WATCH_MODEL_EVENTS": True,

    # Track user login / logout / failed-login Django auth events.
    "WATCH_AUTH_EVENTS": True,

    # Track every HTTP request: URL, method, user, IP, geo, timing.
    "WATCH_REQUEST_EVENTS": True,

    # Track cross-origin requests (requires X-Frontend-URL header from client).
    "WATCH_CORS_EVENTS": True,

    # ──────────────────────────────────────────────────────────────────────────
    # Performance & async
    # ──────────────────────────────────────────────────────────────────────────

    # Use Celery for async log writes (strongly recommended for production).
    # Automatically falls back to synchronous ORM writes when Celery is not
    # configured or the broker is unreachable.
    "ASYNC_ENABLED": True,

    # Backend class that writes log entries to storage.
    #
    #   "activitylog.backends.AsyncBackend"      ← Celery tasks        (default)
    #   "activitylog.backends.ModelBackend"       ← synchronous ORM
    #   "activitylog.backends.MultiBackend"       ← fan-out to N backends
    #   "activitylog.backends.ClickHouseBackend"  ← requires clickhouse-driver
    #   "activitylog.backends.MongoBackend"       ← requires pymongo
    #   "activitylog.backends.ScyllaDBBackend"    ← requires cassandra-driver
    #   "myapp.logging.MyCustomBackend"           ← your own subclass
    "LOGGING_BACKEND": "activitylog.backends.AsyncBackend",

    # List of backend dotted paths — only used with MultiBackend.
    "MULTI_BACKENDS": [
        # "activitylog.backends.ModelBackend",
        # "activitylog.backends.ClickHouseBackend",
    ],

    # ──────────────────────────────────────────────────────────────────────────
    # Request metadata
    # ──────────────────────────────────────────────────────────────────────────

    # WSGI environ key for the real client IP address.
    # Direct access (no proxy):       "REMOTE_ADDR"
    # Behind nginx / AWS ALB / Cloudflare: "HTTP_X_FORWARDED_FOR"
    # Behind Heroku or similar:       "HTTP_X_FORWARDED_FOR"
    "REMOTE_ADDR_HEADER": "REMOTE_ADDR",

    # HTTP Client Hints headers for browser and platform detection.
    # Modern browsers send these automatically with Sec-CH-UA / Sec-CH-UA-Platform.
    "BROWSER_HEADER":  "HTTP_SEC_CH_UA",
    "PLATFORM_HEADER": "HTTP_SEC_CH_UA_PLATFORM",
    "OS_HEADER":       "GNOME_SHELL_SESSION_MODE",

    # Capture HTTP response status code, response time (ms), and body sizes.
    # Requires ActivityLogMiddleware to be placed FIRST in MIDDLEWARE.
    "TRACK_RESPONSE_METRICS": True,

    # ──────────────────────────────────────────────────────────────────────────
    # JWT integration
    # ──────────────────────────────────────────────────────────────────────────

    # Prefix expected in the Authorization header ("Bearer <token>").
    # Change to "JWT" for the older djangorestframework-jwt library.
    "JWT_AUTH_HEADER_PREFIX": "Bearer",

    # Primary signing algorithm used by your JWT provider.
    #
    # Symmetric HMAC  : "HS256" | "HS384" | "HS512"
    # Asymmetric RSA  : "RS256" | "RS384" | "RS512"
    # Asymmetric EC   : "ES256" | "ES384" | "ES512"
    # Asymmetric PSS  : "PS256" | "PS384" | "PS512"
    #
    # Must match the 'alg' header in tokens issued by your auth server.
    "JWT_ALGORITHM": "HS256",

    # All algorithms accepted when decoding incoming tokens.
    # Tokens whose header 'alg' is not in this list are rejected.
    "JWT_ALGORITHMS": [
        "HS256", "HS384", "HS512",
        "RS256", "RS384", "RS512",
        "ES256", "ES384", "ES512",
        "PS256", "PS384", "PS512",
    ],

    # Shared secret for HMAC algorithms (HS256 / HS384 / HS512).
    # None → Django's SECRET_KEY is used automatically.
    # Ignored for asymmetric algorithms (RS* / ES* / PS*).
    "JWT_SECRET_KEY": None,

    # PEM-encoded RSA / EC public key for asymmetric algorithms.
    # Accepts either a PEM string or an absolute file path.
    #
    # Inline PEM string:
    #   "JWT_PUBLIC_KEY": "-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----"
    #
    # File path:
    #   "JWT_PUBLIC_KEY": "/etc/ssl/jwt/public.pem"
    #
    # Required when JWT_VERIFY_SIGNATURE = True and JWT_ALGORITHM is RS* / ES* / PS*.
    "JWT_PUBLIC_KEY": None,

    # Verify JWT signatures during request attribution log writes.
    #
    # False (default) — skip verification. Django's auth middleware already
    #   authenticated the request; we only need the user_id claim for logging.
    #
    # True — re-verify the signature using JWT_SECRET_KEY (HMAC) or
    #   JWT_PUBLIC_KEY (RSA / EC). Adds a small amount of CPU overhead per
    #   logged request.
    "JWT_VERIFY_SIGNATURE": False,

    # ──────────────────────────────────────────────────────────────────────────
    # Database
    # ──────────────────────────────────────────────────────────────────────────

    # Django database alias to use for log writes.
    # Point to a dedicated database to avoid contention with your app DB.
    "DATABASE_ALIAS": "default",

    # Enforce a foreign-key constraint from log entries to the User table.
    "USER_DB_CONSTRAINT": True,

    # Verify that the request user still exists in the DB before logging.
    # Set False if your User table is on a different database than the log table.
    "CHECK_IF_REQUEST_USER_EXISTS": True,

    # ──────────────────────────────────────────────────────────────────────────
    # GeoIP location lookup
    # ──────────────────────────────────────────────────────────────────────────

    # Absolute path to a MaxMind GeoLite2-City.mmdb database file.
    # Download free (registration required):
    #   https://dev.maxmind.com/geoip/geolite2-free-geolocation-data
    #
    # None → the package looks for the file in its own local/ directory.
    # Leave None and skip the mmdb file to log without geo data.
    "GEOIP_PATH": None,

    # ──────────────────────────────────────────────────────────────────────────
    # URL filtering
    # ──────────────────────────────────────────────────────────────────────────

    # Regex patterns for URLs that should NOT be logged (blacklist).
    "UNREGISTERED_URLS": [
        r"^/admin/",
        r"^/static/",
        r"^/favicon\.ico$",
        r"^/health/",
        r"^/metrics/",
    ],

    # Additional patterns appended to UNREGISTERED_URLS.
    # Use this to extend the default list without replacing it.
    "UNREGISTERED_URLS_EXTRA": [
        # r"^/internal/",
    ],

    # If non-empty, ONLY URLs matching these patterns are logged (whitelist).
    # When set, UNREGISTERED_URLS and UNREGISTERED_URLS_EXTRA are ignored.
    "REGISTERED_URLS": [
        # r"^/api/",
    ],

    # ──────────────────────────────────────────────────────────────────────────
    # Model filtering
    # ──────────────────────────────────────────────────────────────────────────

    # Additional model classes or "app_label.ModelName" strings to exclude
    # from CRUD event logging. The package's own models are always excluded.
    "UNREGISTERED_CLASSES_EXTRA": [
        # "myapp.AuditIgnoredModel",
    ],

    # If non-empty, ONLY changes to these models are logged (whitelist).
    "REGISTERED_CLASSES": [
        # "myapp.ImportantModel",
    ],

    # ──────────────────────────────────────────────────────────────────────────
    # CRUD event options
    # ──────────────────────────────────────────────────────────────────────────

    # Skip creating a CRUDEvent when a save() call changed no fields.
    "CRUD_EVENT_NO_CHANGED_FIELDS_SKIP": False,

    # Dotted-path callables called before each CRUD event is created.
    # Returning False from any callback suppresses the event entirely.
    # Example: "myapp.hooks.should_log_crud"
    "CRUD_DIFFERENCE_CALLBACKS": [],

    # ──────────────────────────────────────────────────────────────────────────
    # Security & integrity
    # ──────────────────────────────────────────────────────────────────────────

    # Make all log admin views read-only (disable edit / delete in Django admin).
    "READONLY_EVENTS": False,

    # Re-raise exceptions thrown inside signal handlers.
    # Keep False in production — a logging failure should never break a request.
    "PROPAGATE_EXCEPTIONS": False,

    # ──────────────────────────────────────────────────────────────────────────
    # Real-time streaming
    # ──────────────────────────────────────────────────────────────────────────

    # Enable WebSocket (Django Channels) and SSE streaming of log events.
    # Requires CHANNEL_LAYERS to be configured when True.
    "REALTIME_ENABLED": False,

    # ──────────────────────────────────────────────────────────────────────────
    # Retention
    # ──────────────────────────────────────────────────────────────────────────

    # Global default retention period (days). Logs older than this are deleted
    # by the Celery Beat retention task. None = no automatic deletion.
    # Fine-grained control is available through RetentionPolicy model records.
    "DEFAULT_RETENTION_DAYS": None,

    # ──────────────────────────────────────────────────────────────────────────
    # Django Admin display toggles
    # ──────────────────────────────────────────────────────────────────────────

    "ADMIN_SHOW_MODEL_EVENTS":   True,
    "ADMIN_SHOW_AUTH_EVENTS":    True,
    "ADMIN_SHOW_REQUEST_EVENTS": True,
    "ADMIN_SHOW_CORS_EVENTS":    True,

    # ──────────────────────────────────────────────────────────────────────────
    # Table purge SQL (performance — PostgreSQL / MySQL)
    # ──────────────────────────────────────────────────────────────────────────

    # When set, this raw SQL string is used instead of ORM .delete() for the
    # "Purge all" admin action. Much faster for tables with millions of rows.
    #
    # PostgreSQL example:
    #   "TRUNCATE TABLE \"{db_table}\" RESTART IDENTITY CASCADE"
    #
    # MySQL example:
    #   "TRUNCATE TABLE `{db_table}`"
    "TRUNCATE_TABLE_SQL_STATEMENT": "",
}
```

### Legacy settings (v1 → v2 migration)

All `DJANGO_ACTIVITY_LOG_*` top-level settings from v1 are still read and applied automatically at lower priority than the `ACTIVITYLOG` dict. You can migrate keys one at a time.

```python
# v1 style (still works)
DJANGO_ACTIVITY_LOG_REMOTE_ADDR_HEADER = "HTTP_X_FORWARDED_FOR"

# v2 style (preferred)
ACTIVITYLOG = {
    "REMOTE_ADDR_HEADER": "HTTP_X_FORWARDED_FOR",
}
```

---

## JWT Integration

JWT libraries are auto-detected in priority order. Install whichever you use:

```bash
# Recommended — actively maintained
pip install "django-activitylog-jwt[jwt]"
# Equivalent to:
pip install djangorestframework-simplejwt

# Legacy — still supported
pip install djangorestframework-jwt

# Standalone PyJWT (always available as fallback when simplejwt is installed)
pip install PyJWT
```

No configuration is required when using the default HS256 algorithm with simplejwt — the package auto-detects the installed library and extracts the `user_id` claim from every authenticated request.

### HS256 (default)

HS256 uses a shared secret (your Django `SECRET_KEY` by default). This is the default algorithm for `djangorestframework-simplejwt` and requires no additional setup.

```python
# settings.py

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
}

# Optional — only needed to override defaults
ACTIVITYLOG = {
    "JWT_AUTH_HEADER_PREFIX": "Bearer",  # default
    "JWT_ALGORITHM":          "HS256",   # default
    "JWT_SECRET_KEY":         None,      # None → uses Django SECRET_KEY
    "JWT_VERIFY_SIGNATURE":   False,     # skip re-verification (recommended)
}
```

simplejwt settings (configure in your own project):

```python
from datetime import timedelta

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME":  timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ALGORITHM":              "HS256",
    "SIGNING_KEY":            SECRET_KEY,   # HS256 shared secret
}
```

### RS256 / Asymmetric Algorithms

RS256 uses a private key to sign tokens and a public key to verify them. The auth server holds the private key; this package (and your Django app) only need the public key for optional signature verification.

**Step 1 — Generate an RSA keypair** (skip if your auth server already has keys):

```bash
# Generate private key (keep this secret — auth server only)
openssl genrsa -out private.pem 2048

# Extract public key (share with Django app)
openssl rsa -in private.pem -pubout -out public.pem
```

**Step 2 — Configure simplejwt** to use RS256:

```python
SIMPLE_JWT = {
    "ALGORITHM":      "RS256",
    "SIGNING_KEY":    open("/path/to/private.pem").read(),   # auth server
    "VERIFYING_KEY":  open("/path/to/public.pem").read(),    # Django app
}
```

**Step 3 — Configure activitylog** to match:

```python
ACTIVITYLOG = {
    "JWT_ALGORITHM":        "RS256",
    "JWT_ALGORITHMS":       ["RS256"],        # restrict to RS256 only
    "JWT_PUBLIC_KEY":       "/path/to/public.pem",  # file path or PEM string
    "JWT_VERIFY_SIGNATURE": False,            # True to re-verify in activitylog
}
```

Inline PEM string (alternative to file path):

```python
ACTIVITYLOG = {
    "JWT_ALGORITHM":  "RS256",
    "JWT_PUBLIC_KEY": """
-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA...
-----END PUBLIC KEY-----
""",
}
```

**ECDSA (ES256)** works the same way — generate an EC keypair instead:

```bash
openssl ecparam -name prime256v1 -genkey -noout -out ec-private.pem
openssl ec -in ec-private.pem -pubout -out ec-public.pem
```

```python
SIMPLE_JWT = {
    "ALGORITHM":     "ES256",
    "SIGNING_KEY":   open("ec-private.pem").read(),
    "VERIFYING_KEY": open("ec-public.pem").read(),
}

ACTIVITYLOG = {
    "JWT_ALGORITHM":  "ES256",
    "JWT_ALGORITHMS": ["ES256"],
    "JWT_PUBLIC_KEY": "/path/to/ec-public.pem",
}
```

### Signature Verification

By default, `JWT_VERIFY_SIGNATURE = False`. This is intentional — Django's auth middleware already verified the token before the request reached your views. Re-verifying in activitylog adds CPU overhead for no security benefit.

Set `JWT_VERIFY_SIGNATURE = True` only if you have a specific reason to double-verify (e.g., audit trails that must prove the logged user matched the signed token):

```python
ACTIVITYLOG = {
    "JWT_ALGORITHM":        "RS256",
    "JWT_PUBLIC_KEY":       "/etc/ssl/jwt/public.pem",
    "JWT_VERIFY_SIGNATURE": True,   # re-verify during log attribution
}
```

### Token Claim Mapping

The package extracts the user ID from JWT payloads by checking these claims in order:

| Priority | Claim key | Used by |
|---|---|---|
| 1 | `user_id` | djangorestframework-simplejwt (default) |
| 2 | `sub` | Standard OIDC / RFC 7519 |
| 3 | `pk` | Alternative Django convention |
| 4 | `id` | Generic fallback |

If your token uses a different claim key, override `get_user_id_from_jwt()` in a custom backend.

---

## Proxy & IP Configuration

When your Django app runs behind a reverse proxy (nginx, AWS ALB, Cloudflare), the real client IP arrives in a forwarded header rather than `REMOTE_ADDR`.

```python
ACTIVITYLOG = {
    # Direct deployment (no proxy)
    "REMOTE_ADDR_HEADER": "REMOTE_ADDR",

    # Behind nginx / AWS ALB / Cloudflare / Heroku
    "REMOTE_ADDR_HEADER": "HTTP_X_FORWARDED_FOR",

    # Custom header (e.g., some CDNs use X-Real-IP)
    "REMOTE_ADDR_HEADER": "HTTP_X_REAL_IP",
}
```

When using `HTTP_X_FORWARDED_FOR`, the package automatically strips any chained proxy IPs and uses only the first (leftmost) address, which is the original client.

**Important:** Always configure trusted proxy headers in Django itself (`SECURE_PROXY_SSL_HEADER`, `USE_X_FORWARDED_HOST`) in addition to this setting.

---

## GeoIP Setup

GeoIP enriches every log entry with `latitude`, `longitude`, `city`, `country`, and `country_code`.

**Step 1 — Download the MaxMind GeoLite2-City database** (free, registration required):

Visit [https://dev.maxmind.com/geoip/geolite2-free-geolocation-data](https://dev.maxmind.com/geoip/geolite2-free-geolocation-data) and download `GeoLite2-City.mmdb`.

**Step 2 — Configure the path:**

```python
ACTIVITYLOG = {
    "GEOIP_PATH": "/var/lib/geoip/GeoLite2-City.mmdb",
}
```

When `GEOIP_PATH` is `None`, the package looks for the file at `activitylog/local/GeoLite2-City.mmdb`. Private and loopback IP addresses (127.x, 192.168.x, 10.x, etc.) are skipped automatically — geo fields will be blank for those.

---

## REST API

Mount the router under any prefix:

```python
# urls.py
urlpatterns = [
    path("api/activity/", include("activitylog.api.urls")),
]
```

### Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/api/activity/crud-events/` | GET | List CRUD (model change) events |
| `/api/activity/crud-events/{id}/` | GET | CRUD event detail |
| `/api/activity/crud-events/export_csv/` | GET | Download filtered results as CSV |
| `/api/activity/crud-events/export_json/` | GET | Download filtered results as JSON |
| `/api/activity/crud-events/verify_integrity/` | GET | SHA-256 integrity report |
| `/api/activity/login-events/` | GET | Login / logout / failed-login events |
| `/api/activity/login-events/failed_logins/` | GET | Failed logins only |
| `/api/activity/login-events/brute_force_suspects/` | GET | IPs with ≥ 5 failures in 1 hour |
| `/api/activity/request-events/` | GET | HTTP request log |
| `/api/activity/request-events/slow_requests/` | GET | Requests that took > 1 s |
| `/api/activity/request-events/error_rates/` | GET | 4xx / 5xx aggregation by endpoint |
| `/api/activity/cors-events/` | GET | Cross-origin request log |
| `/api/activity/system-events/` | GET | System / internal error events |
| `/api/activity/system-events/critical/` | GET | CRITICAL severity events only |
| `/api/activity/database-configs/` | GET, POST | Manage database configurations |
| `/api/activity/database-configs/{id}/health_check/` | POST | Run a health check now |
| `/api/activity/database-configs/{id}/test_connection/` | POST | Test connectivity |
| `/api/activity/retention-policies/` | GET, POST, PUT, DELETE | Manage retention rules |
| `/api/activity/retention-policies/{id}/run_now/` | POST | Trigger retention cleanup immediately |
| `/api/activity/dashboard/` | GET | Aggregated stats for a time window |
| `/api/activity/stream/` | GET | SSE real-time event stream |

### Filtering and pagination

All list endpoints accept the following query parameters:

| Parameter | Type | Example |
|---|---|---|
| `date_from` | ISO 8601 datetime | `?date_from=2024-01-01T00:00:00Z` |
| `date_to` | ISO 8601 datetime | `?date_to=2024-01-31T23:59:59Z` |
| `last_hours` | integer | `?last_hours=24` |
| `user_id` | integer | `?user_id=42` |
| `remote_ip` | string | `?remote_ip=203.0.113.5` |
| `search` | string | `?search=admin` |
| `ordering` | field name | `?ordering=-datetime` |
| `page` | integer | `?page=2` |
| `page_size` | 1 – 1000 | `?page_size=100` |

Field-specific filters (e.g., `?method=POST`, `?event_type=create`) require `django-filter`:

```bash
pip install "django-activitylog-jwt[filters]"
```

### DRF authentication

The API endpoints respect your global `DEFAULT_AUTHENTICATION_CLASSES`. For JWT-protected APIs:

```python
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
}
```

---

## CORS Tracking

CORS event tracking captures cross-origin requests when a frontend sends the `X-Frontend-URL` header.

**Frontend (JavaScript):**

```javascript
// Include this header on every API request from your frontend
axios.defaults.headers.common["X-Frontend-URL"] = window.location.href;

// Or with fetch:
fetch("/api/orders/", {
    headers: { "X-Frontend-URL": window.location.href },
});
```

**Backend:**

```python
ACTIVITYLOG = {
    "WATCH_CORS_EVENTS": True,   # default
}
```

Each `CorsEvent` record stores the `origin`, `url`, `method`, `user`, `remote_ip`, and geo data.

---

## Multi-Database Support

### PostgreSQL / MySQL / SQLite (Django ORM)

Route activity logs to a dedicated database to isolate them from your application data:

```python
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "myapp",
        "HOST": "db.example.com",
        "USER": "myapp",
        "PASSWORD": "secret",
    },
    "logs": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "activitylogs",
        "HOST": "logs-db.example.com",
        "USER": "loguser",
        "PASSWORD": "logsecret",
    },
}

ACTIVITYLOG = {
    "DATABASE_ALIAS": "logs",
    "LOGGING_BACKEND": "activitylog.backends.ModelBackend",
    # Set False when User table is on 'default' and logs are on 'logs'
    "USER_DB_CONSTRAINT": False,
    "CHECK_IF_REQUEST_USER_EXISTS": False,
}

# Run migrations on both aliases
# python manage.py migrate activitylog --database=logs
```

### ClickHouse (high-volume analytics)

```bash
pip install "django-activitylog-jwt[clickhouse]"
```

```python
ACTIVITYLOG = {
    "LOGGING_BACKEND": "activitylog.backends.ClickHouseBackend",
}

ACTIVITYLOG_CLICKHOUSE = {
    "host":     "clickhouse.example.com",
    "port":     9000,
    "database": "activitylog",
    "user":     "default",
    "password": "",
}
```

### MongoDB

```bash
pip install "django-activitylog-jwt[mongodb]"
```

```python
ACTIVITYLOG = {
    "LOGGING_BACKEND": "activitylog.backends.MongoBackend",
}

ACTIVITYLOG_MONGODB = {
    "uri":      "mongodb://localhost:27017",
    "database": "activitylog",
}
```

### ScyllaDB / Apache Cassandra

```bash
pip install "django-activitylog-jwt[scylladb]"
```

```python
ACTIVITYLOG = {
    "LOGGING_BACKEND": "activitylog.backends.ScyllaDBBackend",
}

ACTIVITYLOG_SCYLLADB = {
    "contact_points": ["scylla1.example.com", "scylla2.example.com"],
    "port":           9042,
    "keyspace":       "activitylog",
}
```

### Fan-out to multiple backends simultaneously

```python
ACTIVITYLOG = {
    "LOGGING_BACKEND": "activitylog.backends.MultiBackend",
    "MULTI_BACKENDS": [
        "activitylog.backends.ModelBackend",      # keep in PostgreSQL
        "activitylog.backends.ClickHouseBackend", # also stream to ClickHouse
    ],
}
```

### Dynamic per-tenant database routing

Create `DatabaseConfig` records in Django admin or via the REST API. The `ActivityLogDatabaseRouter` queries active configs at runtime and registers them as Django database aliases automatically — no server restart required.

```python
# settings.py
DATABASE_ROUTERS = ["activitylog.routing.routers.ActivityLogDatabaseRouter"]
```

To encrypt database passwords at rest (Fernet AES-128, key derived from `SECRET_KEY`):

```bash
pip install "django-activitylog-jwt[encryption]"
```

---

## Async Processing with Celery

```bash
pip install "django-activitylog-jwt[celery]"
```

```python
# settings.py
CELERY_BROKER_URL    = "redis://localhost:6379/0"
CELERY_RESULT_BACKEND = "redis://localhost:6379/0"

ACTIVITYLOG = {
    "ASYNC_ENABLED":  True,
    "LOGGING_BACKEND": "activitylog.backends.AsyncBackend",
}
```

Include the built-in Celery Beat schedule for daily retention enforcement and database health checks:

```python
# celery.py  (or wherever you configure Celery Beat)
import activitylog.settings as al_settings

app.conf.beat_schedule = {
    **al_settings.CELERY_BEAT_SCHEDULE,
    # Add your own schedules here
}
```

When `ASYNC_ENABLED = True` but the broker is unreachable, the package falls back to synchronous ORM writes automatically — your application will never raise an exception due to a logging failure.

**Start the worker and beat scheduler:**

```bash
celery -A myproject worker --loglevel=info
celery -A myproject beat   --loglevel=info
```

---

## Real-Time Streaming

### Server-Sent Events (SSE)

No extra packages required. The SSE endpoint polls the database every 2 seconds and pushes new events to connected clients.

```
GET /api/activity/stream/
```

```javascript
const source = new EventSource("/api/activity/stream/", { withCredentials: true });

source.onmessage = (event) => {
    const log = JSON.parse(event.data);
    console.log(log);
};

source.onerror = () => source.close();
```

### WebSocket (Django Channels)

```bash
pip install "django-activitylog-jwt[websocket]"
# Installs: channels>=4.0.0  channels-redis>=4.1.0
```

```python
# settings.py
INSTALLED_APPS = [
    ...
    "channels",
    "activitylog",
]

ASGI_APPLICATION = "myproject.asgi.application"

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG":  {"hosts": [("localhost", 6379)]},
    }
}

ACTIVITYLOG = {
    "REALTIME_ENABLED": True,
}
```

```python
# asgi.py
import os
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from django.urls import path
from activitylog.consumers.log_consumer import ActivityLogConsumer

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myproject.settings")

application = ProtocolTypeRouter({
    "http":      get_asgi_application(),
    "websocket": URLRouter([
        path("ws/activity/", ActivityLogConsumer.as_asgi()),
    ]),
})
```

```javascript
const ws = new WebSocket("wss://yoursite.com/ws/activity/");

ws.onopen    = () => console.log("Connected to activity log stream");
ws.onmessage = (e) => console.log("New event:", JSON.parse(e.data));
ws.onclose   = (e) => console.log("Disconnected:", e.code, e.reason);
```

WebSocket authentication is enforced: unauthenticated connections are closed with code **4001**, connections without the `view_logs` permission are closed with **4003**.

---

## Retention Policies

### Global default

```python
ACTIVITYLOG = {
    "DEFAULT_RETENTION_DAYS": 90,   # delete all logs older than 90 days
}
```

### Per-event-type policies

Create `RetentionPolicy` records in Django admin or via the REST API for fine-grained control:

| Field | Type | Description |
|---|---|---|
| `name` | string | Human-readable label |
| `event_type` | choice | `crud` / `login` / `request` / `cors` / `system` |
| `retain_days` | integer | Keep logs for this many days |
| `is_active` | boolean | Toggle without deleting the policy |
| `tenant_id` | string | Scope to a specific tenant (optional) |

The Celery Beat task `enforce_retention_policies` runs daily by default. Trigger it immediately via the API:

```
POST /api/activity/retention-policies/{id}/run_now/
```

### Management command

```bash
# Delete all logs older than 30 days
python manage.py cleanup_logs --days 30

# Target a specific event type
python manage.py cleanup_logs --days 30 --event-type login

# Dry run — show what would be deleted without deleting
python manage.py cleanup_logs --days 30 --dry-run
```

---

## Integrity Verification

Every log entry stores a SHA-256 hash of its key fields at write time. Any out-of-band modification to the row causes `verify_integrity()` to return `False`.

### Django admin

Each admin list view displays an **Integrity** column with a green checkmark (verified) or red cross (tampered / missing hash).

### REST API

```
GET /api/activity/crud-events/verify_integrity/
```

```json
{
    "total":        1500,
    "verified":     1498,
    "tampered":     2,
    "tampered_ids": ["3f2a1b...", "9c8d7e..."]
}
```

### Management command

```bash
# Report integrity status across all event tables
python manage.py verify_log_integrity

# Recompute missing hashes (does not fix tampered records — that's intentional)
python manage.py verify_log_integrity --fix

# Target a specific model
python manage.py verify_log_integrity --model CRUDEvent
python manage.py verify_log_integrity --model LoginEvent
python manage.py verify_log_integrity --model RequestEvent
```

---

## Admin Configuration

The Django admin is auto-configured when `activitylog` is in `INSTALLED_APPS`. Toggle each log type's admin panel independently:

```python
ACTIVITYLOG = {
    "ADMIN_SHOW_MODEL_EVENTS":   True,
    "ADMIN_SHOW_AUTH_EVENTS":    True,
    "ADMIN_SHOW_REQUEST_EVENTS": True,
    "ADMIN_SHOW_CORS_EVENTS":    True,
}
```

Make all log admin views read-only (prevents accidental edits through the admin):

```python
ACTIVITYLOG = {
    "READONLY_EVENTS": True,
}
```

For tables with millions of rows, use raw SQL truncation instead of Django ORM `.delete()` in the admin "Purge all" action:

```python
ACTIVITYLOG = {
    # PostgreSQL
    "TRUNCATE_TABLE_SQL_STATEMENT": 'TRUNCATE TABLE "{db_table}" RESTART IDENTITY CASCADE',

    # MySQL
    # "TRUNCATE_TABLE_SQL_STATEMENT": "TRUNCATE TABLE `{db_table}`",
}
```

---

## Permissions (RBAC)

| Codename | Description |
|---|---|
| `activitylog.view_logs` | View own activity logs (GET only) |
| `activitylog.view_all_logs` | View all users' activity logs |
| `activitylog.manage_database_config` | Create / update / delete `DatabaseConfig` records |

Superusers bypass all permission checks. Assign permissions via Django admin → Users → User permissions, or programmatically:

```python
from django.contrib.auth.models import Permission
from django.contrib.auth import get_user_model

User = get_user_model()
user = User.objects.get(username="analyst")
perm = Permission.objects.get(codename="view_all_logs")
user.user_permissions.add(perm)
```

---

## Management Commands

| Command | Options | Description |
|---|---|---|
| `python manage.py cleanup_logs` | `--days N` `--event-type TYPE` `--dry-run` | Delete old log entries |
| `python manage.py verify_log_integrity` | `--fix` `--model MODEL` | Check / recompute integrity hashes |

---

## Optional Dependencies

| Extra | Packages installed | Use case |
|---|---|---|
| `celery` | `celery>=5.3.0` | Async log writes |
| `jwt` | `djangorestframework-simplejwt>=5.3.0` | JWT auth (recommended) |
| `filters` | `django-filter>=23.0` | Field-level API filtering |
| `websocket` | `channels>=4.0.0`, `channels-redis>=4.1.0` | WebSocket real-time stream |
| `clickhouse` | `clickhouse-driver>=0.2.7` | ClickHouse backend |
| `mongodb` | `pymongo>=4.6.0` | MongoDB backend |
| `scylladb` | `cassandra-driver>=3.28.0` | ScyllaDB / Cassandra backend |
| `encryption` | `cryptography>=42.0.0` | Fernet credential encryption |
| `excel` | `openpyxl>=3.1.0` | Excel export from API |
| `dev` | pytest, ruff, mypy, stubs… | Development and testing |
| `all` | All of the above (except `dev`) | Everything |

```bash
# Install specific extras
pip install "django-activitylog-jwt[celery,jwt,filters]"

# Install everything
pip install "django-activitylog-jwt[all]"
```

---

## Third-Party Auth Compatibility

| Library | Supported | Notes |
|---|---|---|
| `djangorestframework-simplejwt` | Yes | Auto-detected, recommended |
| `djangorestframework-jwt` (legacy) | Yes | Auto-detected via `jwt_decode_handler` |
| `PyJWT` (standalone) | Yes | Direct decode fallback |
| `django-allauth` | Yes | Uses session auth — no extra config |
| `dj-rest-auth` | Yes | Works with any JWT backend above |
| `social-auth-app-django` | Yes | Uses session auth — no extra config |
| Custom OIDC providers (RS256) | Yes | Configure `JWT_ALGORITHM` + `JWT_PUBLIC_KEY` |

---

## Custom Backends

Subclass `BaseBackend` and implement five write methods:

```python
# myapp/logging.py
from activitylog.backends import BaseBackend

class SplunkBackend(BaseBackend):
    def crud(self, data: dict) -> None:
        self._send(data)

    def login(self, data: dict) -> None:
        self._send(data)

    def request(self, data: dict) -> None:
        self._send(data)

    def cors(self, data: dict) -> None:
        self._send(data)

    def system(self, data: dict) -> None:
        self._send(data)

    def _send(self, data: dict) -> None:
        import requests
        requests.post("https://splunk.example.com/services/collector/event",
                      json={"event": data},
                      headers={"Authorization": "Splunk <HEC_TOKEN>"})
```

```python
ACTIVITYLOG = {
    "LOGGING_BACKEND": "myapp.logging.SplunkBackend",
}
```

---

## Upgrading from v1

### Step 1 — Update your settings

```python
# v1
DJANGO_ACTIVITY_LOG_REMOTE_ADDR_HEADER = "HTTP_X_FORWARDED_FOR"
DJANGO_ACTIVITY_LOG_LOGGING_BACKEND = "activitylog.backends.ModelBackend"

# v2 — migrate to the ACTIVITYLOG dict
ACTIVITYLOG = {
    "REMOTE_ADDR_HEADER": "HTTP_X_FORWARDED_FOR",
    "LOGGING_BACKEND":    "activitylog.backends.ModelBackend",
}
```

Old `DJANGO_ACTIVITY_LOG_*` keys still work and are merged automatically at lower priority, so you can migrate key-by-key without a flag day.

### Step 2 — Run the new migration

```bash
python manage.py migrate activitylog
```

Migration `0002_enhanced_models` adds:

- `integrity_hash`, `extra_data`, `user_agent`, `country_code` to all event tables
- `response_status`, `response_time_ms`, `request_body_size`, `response_body_size` to `RequestEvent`
- `origin`, `allowed` to `CorsEvent`
- New tables: `SystemEvent`, `DatabaseConfig`, `RetentionPolicy`
- Composite database indexes on high-cardinality field combinations

### Step 3 — Remove the hard JWT dependency

`rest_framework_jwt` is no longer required. The package auto-detects whichever JWT library is installed:

```bash
# Switch from legacy to simplejwt
pip uninstall djangorestframework-jwt
pip install djangorestframework-simplejwt
```

### Step 4 — Verify middleware order

`ActivityLogMiddleware` must be **first** in `MIDDLEWARE` for response metric capture (`TRACK_RESPONSE_METRICS`) to work correctly. If it was not first in v1, move it.

### Step 5 — Optional — enable JWT algorithm settings

If you use RS256 or another asymmetric algorithm, add the new JWT settings:

```python
ACTIVITYLOG = {
    "JWT_ALGORITHM":  "RS256",
    "JWT_PUBLIC_KEY": "/path/to/public.pem",
}
```

---

## Development

```bash
git clone https://github.com/knand4930/django-activitylog-jwt
cd django-activitylog-jwt
pip install -e ".[dev]"
```

**Run the test suite:**

```bash
pytest
```

**Run tests for a specific Django version with tox:**

```bash
tox -e py312-django50
tox -e py310-django42
```

**Lint and format:**

```bash
ruff check activitylog/
ruff format activitylog/
```

**Type checking:**

```bash
mypy activitylog/
```

---

## License

MIT — see [LICENSE](LICENSE).

## Author

**Nand Kishore** — [knand4930@gmail.com](mailto:knand4930@gmail.com)

GitHub: [https://github.com/knand4930/django-activitylog-jwt](https://github.com/knand4930/django-activitylog-jwt)
