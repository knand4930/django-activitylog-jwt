"""Utility helpers for the activity log package."""

from __future__ import annotations

import datetime as dt
import logging
import os
from typing import Any, Dict, Optional

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import NOT_PROVIDED, DateTimeField
from django.utils import timezone
from django.utils.encoding import smart_str

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Field-level diffing
# ---------------------------------------------------------------------------

def get_field_value(obj, field) -> Any:
    if isinstance(field, DateTimeField):
        try:
            value = field.to_python(getattr(obj, field.name, None))
            if value is not None and settings.USE_TZ and not timezone.is_naive(value):
                value = timezone.make_naive(value, timezone=dt.timezone.utc)
        except ObjectDoesNotExist:
            value = field.default if field.default is not NOT_PROVIDED else None
    else:
        try:
            value = smart_str(getattr(obj, field.name, None))
        except ObjectDoesNotExist:
            value = field.default if field.default is not NOT_PROVIDED else None
    return value


def model_delta(old_model, new_model) -> Optional[Dict[str, Any]]:
    delta = {}
    for field in new_model._meta.fields:
        old_val = get_field_value(old_model, field)
        new_val = get_field_value(new_model, field)
        if old_val != new_val:
            delta[field.name] = [smart_str(old_val), smart_str(new_val)]
    return delta or None


def get_m2m_field_name(model, instance) -> Optional[str]:
    for x in model._meta.related_objects:
        if x.related_model().__class__ == instance.__class__:
            return x.remote_field.name
    return None


# ---------------------------------------------------------------------------
# GeoIP lookup
# ---------------------------------------------------------------------------

_GEOIP_PATH = getattr(
    settings,
    "DJANGO_ACTIVITY_LOG_GEOIP_PATH",
    os.path.join(os.path.dirname(__file__), "local", "GeoLite2-City.mmdb"),
)

_GEO_READER = None


def _get_geo_reader():
    global _GEOIP_PATH, _GEO_READER
    if _GEO_READER is not None:
        return _GEO_READER
    try:
        import geoip2.database
        if os.path.exists(_GEOIP_PATH):
            _GEO_READER = geoip2.database.Reader(_GEOIP_PATH)
    except Exception:
        pass
    return _GEO_READER


def get_geo_data(ip: Optional[str]) -> Dict[str, Optional[str]]:
    """Return a dict with latitude, longitude, city, country, country_code for an IP."""
    empty: Dict[str, Optional[str]] = {
        "latitude": None,
        "longitude": None,
        "city": None,
        "country": None,
        "country_code": None,
    }
    if not ip:
        return empty

    # Skip private / loopback ranges quickly
    if ip.startswith(("10.", "192.168.", "127.", "::1", "172.")):
        return empty

    reader = _get_geo_reader()
    if reader is None:
        return empty

    try:
        record = reader.city(ip)
        return {
            "latitude": str(record.location.latitude) if record.location.latitude else None,
            "longitude": str(record.location.longitude) if record.location.longitude else None,
            "city": record.city.name,
            "country": record.country.name,
            "country_code": record.country.iso_code,
        }
    except Exception:
        return empty


# ---------------------------------------------------------------------------
# Misc
# ---------------------------------------------------------------------------

def should_propagate_exceptions() -> bool:
    return bool(getattr(settings, "DJANGO_ACTIVITY_LOG_PROPAGATE_EXCEPTIONS", False))


def get_model_list(class_list: list) -> None:
    from django.apps import apps
    for idx, item in enumerate(class_list):
        if isinstance(item, str):
            class_list[idx] = apps.get_model(item)
