import contextlib

from django.contrib.auth import get_user_model, signals
from django.db import transaction
from django.utils.module_loading import import_string
from activitylog.middleware.middleware import get_current_request, set_local_details
from activitylog.models import LoginEvent
from django.contrib.gis.geoip2 import GeoIP2

from activitylog.settings import (
    DATABASE_ALIAS,
    LOGGING_BACKEND,
    REMOTE_ADDR_HEADER,
    WATCH_AUTH_EVENTS, HTTP_SEC_CH_UA, HTTP_SEC_CH_UA_PLATFORM, GNOME_SHELL_SESSION_MODE,
)
from activitylog.utils import should_propagate_exceptions

audit_logger = import_string(LOGGING_BACKEND)()


def get_user_auth_location():
    remote_ip = None
    browser = None
    platform = None
    operating_system = None
    with contextlib.suppress(Exception):
        address = set_local_details()
        remote_ip = address.META.get(REMOTE_ADDR_HEADER, None)
        browser = address.META.get(HTTP_SEC_CH_UA, None)
        platform = address.META.get(HTTP_SEC_CH_UA_PLATFORM, None)
        operating_system = address.META.get(GNOME_SHELL_SESSION_MODE, None)

    return remote_ip, browser, platform, operating_system


def user_logged_in(sender, request, user, **kwargs):
    remote_ip, browser, platform, operating_system = get_user_auth_location()
    try:
        g = GeoIP2()
        lat, long = g.lat_lon(remote_ip)
        city = g.city(remote_ip)
        country = g.country(remote_ip)
    except Exception:
        lat = None
        long = None
        city = None
        country = None

    print(remote_ip, "remote ip has been printed !!")

    try:
        with transaction.atomic(using=DATABASE_ALIAS):
            audit_logger.login(
                {
                    "login_type": LoginEvent.LOGIN,
                    "username": getattr(user, user.USERNAME_FIELD),
                    "user_id": getattr(user, "id", None),
                    "remote_ip": remote_ip,
                    "latitude": lat,
                    "longitude": long,
                    "city": city,
                    "country": country,
                    "browser": browser,
                    "platform": platform,
                    "operating_system": operating_system,
                }
            )
    except Exception:
        if should_propagate_exceptions():
            raise


def user_logged_out(sender, request, user, **kwargs):
    try:
        with transaction.atomic(using=DATABASE_ALIAS):
            audit_logger.login(
                {
                    "login_type": LoginEvent.LOGOUT,
                    "username": getattr(user, user.USERNAME_FIELD),
                    "user_id": getattr(user, "id", None),
                    "remote_ip": request.META.get(REMOTE_ADDR_HEADER, ""),
                    "browser": request.META.get(HTTP_SEC_CH_UA, ""),
                    "platform": request.META.get(HTTP_SEC_CH_UA_PLATFORM, ""),
                    "operating_system": request.META.get(GNOME_SHELL_SESSION_MODE, ""),
                }
            )
    except Exception:
        if should_propagate_exceptions():
            raise


def user_login_failed(sender, credentials, **kwargs):
    try:
        with transaction.atomic(using=DATABASE_ALIAS):
            request = get_current_request()
            user_model = get_user_model()
            audit_logger.login(
                {
                    "login_type": LoginEvent.FAILED,
                    "username": credentials[user_model.USERNAME_FIELD],
                    "remote_ip": request.META.get(REMOTE_ADDR_HEADER, ""),
                    "browser": request.META.get(HTTP_SEC_CH_UA, ""),
                    "platform": request.META.get(HTTP_SEC_CH_UA_PLATFORM, ""),
                    "operating_system": request.META.get(GNOME_SHELL_SESSION_MODE, ""),
                }
            )
            # print()
    except Exception:
        if should_propagate_exceptions():
            raise


if WATCH_AUTH_EVENTS:
    signals.user_logged_in.connect(
        user_logged_in, dispatch_uid="activity_log_signals_logged_in"
    )
    signals.user_logged_out.connect(
        user_logged_out, dispatch_uid="activity_log_signals_logged_out"
    )
    signals.user_login_failed.connect(
        user_login_failed, dispatch_uid="activity_log_signals_login_failed"
    )
