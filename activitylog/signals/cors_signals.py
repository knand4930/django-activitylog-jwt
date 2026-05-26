"""Signal handler: captures CORS preflight and cross-origin request events."""

from __future__ import annotations

import logging
import re
from importlib import import_module

from django.conf import settings
from django.core.signals import request_started

from activitylog.settings import (
    GNOME_SHELL_SESSION_MODE,
    HTTP_SEC_CH_UA,
    HTTP_SEC_CH_UA_PLATFORM,
    REGISTERED_URLS,
    REMOTE_ADDR_HEADER,
    UNREGISTERED_URLS,
    WATCH_CORS_EVENTS,
)
from activitylog.utils import get_geo_data

logger = logging.getLogger(__name__)

session_engine = import_module(settings.SESSION_ENGINE)


def _should_log_url(path: str) -> bool:
    for pattern in UNREGISTERED_URLS:
        if re.compile(pattern).match(path):
            return False
    if REGISTERED_URLS:
        return any(re.compile(p).match(path) for p in REGISTERED_URLS)
    return True


def _resolve_user_from_request(cookie_string, authorization_header: str):
    from django.contrib.auth import SESSION_KEY as AUTH_SESSION_KEY
    from django.contrib.auth import get_user_model
    from django.http.cookie import SimpleCookie

    User = get_user_model()

    if cookie_string:
        if isinstance(cookie_string, bytes):
            cookie_string = cookie_string.decode("utf-8", errors="replace")
        cookie = SimpleCookie()
        cookie.load(cookie_string)
        session_name = settings.SESSION_COOKIE_NAME
        if session_name in cookie:
            try:
                session = session_engine.SessionStore(
                    session_key=cookie[session_name].value
                ).load()
                if AUTH_SESSION_KEY in session:
                    return User.objects.get(pk=session[AUTH_SESSION_KEY])
            except Exception:
                pass

    if authorization_header:
        parts = authorization_header.split()
        token = parts[-1] if parts else ""
        user_id = _decode_jwt(token)
        if user_id:
            try:
                return User.objects.get(pk=user_id)
            except User.DoesNotExist:
                pass

    return None


def _decode_jwt(token: str) -> str | None:
    """Return user_id claim from a JWT token (HS256 and RS256 both supported)."""
    from activitylog.compat import get_user_id_from_jwt
    return get_user_id_from_jwt(token)


def cors_started_handler(sender, **kwargs) -> None:  # noqa: ARG001
    from activitylog.tasks.log_tasks import dispatch_log_task

    environ = kwargs.get("environ")
    scope = kwargs.get("scope")

    if environ:
        frontend_url = environ.get("HTTP_X_FRONTEND_URL")
        if not frontend_url:
            return
        path = environ.get("PATH_INFO", "")
        if not _should_log_url(path) or not _should_log_url(frontend_url):
            return

        method = environ.get("HTTP_URL_METHOD") or environ.get("REQUEST_METHOD", "")
        query_string = environ.get("QUERY_STRING", "")
        remote_ip = environ.get(REMOTE_ADDR_HEADER) or environ.get("REMOTE_ADDR")
        cookie_string = environ.get("HTTP_COOKIE", "")
        authorization = environ.get("HTTP_AUTHORIZATION", "")
        browser = environ.get(HTTP_SEC_CH_UA)
        platform = environ.get(HTTP_SEC_CH_UA_PLATFORM)
        operating_system = environ.get(GNOME_SHELL_SESSION_MODE)
    elif scope:
        headers = dict(scope.get("headers", []))
        frontend_url = headers.get(b"x-frontend-url", b"").decode("utf-8", errors="replace")
        if not frontend_url:
            return
        path = scope.get("path", "")
        if not _should_log_url(path):
            return

        method = scope.get("method", "")
        query_string = (scope.get("query_string") or b"").decode("utf-8", errors="replace")
        remote_ip = next(iter(scope.get("client", ("", 0))), "")
        cookie_string = headers.get(b"cookie", b"")
        authorization = headers.get(b"authorization", b"").decode("utf-8", errors="replace")
        browser = platform = operating_system = None
    else:
        return

    user = _resolve_user_from_request(cookie_string, authorization)
    geo = get_geo_data(remote_ip)

    dispatch_log_task("cors", {
        "url": frontend_url[:2048],
        "method": method,
        "query_string": str(query_string)[:4096] if query_string else "",
        "user_id": getattr(user, "id", None),
        "remote_ip": remote_ip,
        "browser": browser,
        "platform": platform,
        "operating_system": operating_system,
        "origin": environ.get("HTTP_ORIGIN") if environ else None,
        **geo,
    })


if WATCH_CORS_EVENTS:
    request_started.connect(
        cors_started_handler,
        dispatch_uid="activity_log_signals_cors_started",
    )
