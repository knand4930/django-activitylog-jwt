"""Version-detection shims for Django 4.x – 6.x and Python 3.8 – 3.14+.

Import from here rather than testing ``django.VERSION`` inline so that all
compatibility logic lives in one place and is easy to update as new releases
ship.
"""

from __future__ import annotations

import sys
from typing import Any

import django

# ---------------------------------------------------------------------------
# Version tuples
# ---------------------------------------------------------------------------

DJANGO_VERSION: tuple[int, ...] = django.VERSION[:3]
PYTHON_VERSION: tuple[int, ...] = sys.version_info[:3]

# Major feature flags — extend as Django 6+ ships
DJANGO_4 = DJANGO_VERSION >= (4, 0)
DJANGO_42 = DJANGO_VERSION >= (4, 2)
DJANGO_50 = DJANGO_VERSION >= (5, 0)
DJANGO_51 = DJANGO_VERSION >= (5, 1)
DJANGO_60 = DJANGO_VERSION >= (6, 0)  # future-proof

PYTHON_310 = PYTHON_VERSION >= (3, 10)
PYTHON_311 = PYTHON_VERSION >= (3, 11)
PYTHON_312 = PYTHON_VERSION >= (3, 12)
PYTHON_313 = PYTHON_VERSION >= (3, 13)
PYTHON_314 = PYTHON_VERSION >= (3, 14)

# ---------------------------------------------------------------------------
# Optional library detection
# ---------------------------------------------------------------------------


def _has(module: str) -> bool:
    import importlib.util

    return importlib.util.find_spec(module) is not None


HAS_CELERY = _has("celery")
HAS_CHANNELS = _has("channels")
HAS_CRYPTOGRAPHY = _has("cryptography")
HAS_DJANGO_FILTER = _has("django_filters")
HAS_CLICKHOUSE = _has("clickhouse_driver")
HAS_PYMONGO = _has("pymongo")
HAS_CASSANDRA = _has("cassandra")
HAS_OPENPYXL = _has("openpyxl")

# JWT library detection (precedence: simplejwt > legacy jwt > PyJWT)
HAS_SIMPLEJWT = _has("rest_framework_simplejwt")
HAS_LEGACY_JWT = _has("rest_framework_jwt")
HAS_PYJWT = _has("jwt")

# ---------------------------------------------------------------------------
# Django API compatibility helpers
# ---------------------------------------------------------------------------


def get_default_db_alias() -> str:
    """Return the Django default database alias string."""
    from django.db import DEFAULT_DB_ALIAS

    return DEFAULT_DB_ALIAS


def get_on_delete_set_null():
    """django.db.models.deletion.SET_NULL — available across all supported versions."""
    from django.db.models import SET_NULL

    return SET_NULL


def make_index(*fields: str, name: str | None = None):
    """Return a ``models.Index`` compatible with Django 4.x – 6.x."""
    from django.db.models import Index

    kwargs: dict[str, Any] = {"fields": list(fields)}
    if name:
        kwargs["name"] = name
    return Index(**kwargs)


def url_path(route: str, view, name: str | None = None):
    """Return a URL pattern using ``path()`` (preferred) or ``re_path()`` as
    a fallback.  ``re_path`` is still available on all supported Django versions
    but this helper makes it easy to migrate in the future."""
    from django.urls import path

    return path(route, view, name=name)


# ---------------------------------------------------------------------------
# JWT decoding helper — HS256 and RS256 (and all JOSE algorithms)
# ---------------------------------------------------------------------------


def _is_asymmetric_algorithm(algorithm: str) -> bool:
    """Return True for RSA, EC, and PSS algorithms (need a public key)."""
    return algorithm.startswith(("RS", "ES", "PS"))


def decode_jwt_token(token: str) -> dict | None:
    """Decode a JWT token payload for request attribution (user_id extraction).

    Supports HS256, RS256, and every other algorithm listed in
    ``ACTIVITYLOG["JWT_ALGORITHMS"]``.

    Signature verification is **off by default** because Django's auth
    middleware already authenticates the request — we only need the
    ``user_id`` / ``sub`` claim to attribute log entries.  Set
    ``ACTIVITYLOG["JWT_VERIFY_SIGNATURE"] = True`` to enable verification.

    Priority order:
      1. PyJWT (covers simplejwt tokens — simplejwt depends on PyJWT)
      2. Legacy djangorestframework-jwt decode handler
    """
    # Deferred import to avoid circular reference at module load time.
    try:
        from activitylog.conf import activitylog_settings

        verify = activitylog_settings.JWT_VERIFY_SIGNATURE
        algorithms = activitylog_settings.JWT_ALGORITHMS
        algorithm = activitylog_settings.JWT_ALGORITHM
    except Exception:
        verify = False
        algorithms = [
            "HS256",
            "RS256",
            "RS384",
            "RS512",
            "ES256",
            "ES384",
            "ES512",
            "HS384",
            "HS512",
            "PS256",
            "PS384",
            "PS512",
        ]
        algorithm = "HS256"

    # ------------------------------------------------------------------
    # Strategy 1: PyJWT
    #   - simplejwt depends on PyJWT, so HAS_SIMPLEJWT ⇒ HAS_PYJWT.
    #   - We bypass UntypedToken / AccessToken (which run DRF validators
    #     including expiry and type checks) and go directly to PyJWT so
    #     the decode works regardless of token type or expiry.
    # ------------------------------------------------------------------
    if HAS_PYJWT or HAS_SIMPLEJWT:
        try:
            import jwt as pyjwt

            if verify:
                if _is_asymmetric_algorithm(algorithm):
                    try:
                        from activitylog.conf import activitylog_settings as _s

                        raw_key = _s.JWT_PUBLIC_KEY or ""
                    except Exception:
                        raw_key = ""
                    # Accept a file path as well as a PEM string.
                    import os

                    if raw_key and os.path.isfile(raw_key):
                        with open(raw_key, "rb") as fh:
                            raw_key = fh.read()
                    key = raw_key
                else:
                    try:
                        from activitylog.conf import activitylog_settings as _s

                        secret = _s.JWT_SECRET_KEY
                    except Exception:
                        secret = None
                    if not secret:
                        from django.conf import settings as _dj

                        secret = _dj.SECRET_KEY
                    key = secret
                return pyjwt.decode(token, key, algorithms=algorithms)
            else:
                return pyjwt.decode(
                    token,
                    options={"verify_signature": False},
                    algorithms=algorithms,
                )
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Strategy 2: legacy djangorestframework-jwt
    #   Uses its own decode handler which respects JWT_AUTH settings.
    # ------------------------------------------------------------------
    if HAS_LEGACY_JWT:
        try:
            from rest_framework_jwt.utils import jwt_decode_handler

            return jwt_decode_handler(token)
        except Exception:
            pass

    return None


def get_user_id_from_jwt(token: str) -> str | None:
    """Extract the user PK from a JWT token payload.

    Checks claims in priority order: ``user_id`` → ``sub`` → ``pk`` → ``id``.
    Returns ``None`` when the token cannot be decoded or contains none of those
    claims.
    """
    payload = decode_jwt_token(token)
    if payload is None:
        return None
    return payload.get("user_id") or payload.get("sub") or payload.get("pk") or payload.get("id")


# ---------------------------------------------------------------------------
# Django deprecation-safe admin helpers
# ---------------------------------------------------------------------------


def admin_display(**kwargs):
    """Wrap ``@admin.display`` safely across Django 3.2 – 6.x.

    Django 3.2 introduced ``@admin.display``; before that, attribute assignment
    was required.  Since we target Django 4.x+, this is always safe.
    """
    from django.contrib import admin

    return admin.display(**kwargs)


# ---------------------------------------------------------------------------
# Helpful assert for startup validation
# ---------------------------------------------------------------------------


def assert_django_compatible() -> None:
    """Raise ``ImproperlyConfigured`` if the runtime Django version is too old."""
    from django.core.exceptions import ImproperlyConfigured

    if DJANGO_VERSION < (4, 0):
        raise ImproperlyConfigured(
            f"django-activitylog-jwt requires Django >= 4.0. "
            f"You are running Django {'.'.join(str(v) for v in DJANGO_VERSION)}."
        )
    if PYTHON_VERSION < (3, 8):
        raise ImproperlyConfigured(
            f"django-activitylog-jwt requires Python >= 3.8. "
            f"You are running Python {'.'.join(str(v) for v in PYTHON_VERSION)}."
        )
