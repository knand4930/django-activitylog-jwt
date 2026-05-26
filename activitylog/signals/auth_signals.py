"""Signal handlers for authentication events (login / logout / failed login)."""

from __future__ import annotations

import logging

from django.contrib.auth import signals

from activitylog.middleware.middleware import set_local_details
from activitylog.settings import (
    GNOME_SHELL_SESSION_MODE,
    HTTP_SEC_CH_UA,
    HTTP_SEC_CH_UA_PLATFORM,
    REMOTE_ADDR_HEADER,
    WATCH_AUTH_EVENTS,
)
from activitylog.utils import get_geo_data, should_propagate_exceptions

logger = logging.getLogger(__name__)


def _request_meta(request) -> dict:
    return {
        "remote_ip": request.META.get(REMOTE_ADDR_HEADER, ""),
        "browser": request.META.get(HTTP_SEC_CH_UA, ""),
        "platform": request.META.get(HTTP_SEC_CH_UA_PLATFORM, ""),
        "operating_system": request.META.get(GNOME_SHELL_SESSION_MODE, ""),
        "user_agent": request.META.get("HTTP_USER_AGENT", ""),
    }


def user_logged_in(sender, request, user, **kwargs) -> None:  # noqa: ARG001
    from activitylog.models import LoginEvent
    from activitylog.tasks.log_tasks import dispatch_log_task

    meta = _request_meta(request)
    geo = get_geo_data(meta["remote_ip"])

    try:
        dispatch_log_task(
            "login",
            {
                "login_type": LoginEvent.LOGIN,
                "username": getattr(user, user.USERNAME_FIELD, ""),
                "user_id": getattr(user, "id", None),
                **meta,
                **geo,
            },
        )
    except Exception:
        logger.exception("auth_signals.user_logged_in failed")
        if should_propagate_exceptions():
            raise


def user_logged_out(sender, request, user, **kwargs) -> None:  # noqa: ARG001
    from activitylog.models import LoginEvent
    from activitylog.tasks.log_tasks import dispatch_log_task

    if user is None:
        return

    meta = _request_meta(request)
    geo = get_geo_data(meta["remote_ip"])

    try:
        dispatch_log_task(
            "login",
            {
                "login_type": LoginEvent.LOGOUT,
                "username": getattr(user, user.USERNAME_FIELD, ""),
                "user_id": getattr(user, "id", None),
                **meta,
                **geo,
            },
        )
    except Exception:
        logger.exception("auth_signals.user_logged_out failed")
        if should_propagate_exceptions():
            raise


def user_login_failed(sender, credentials, **kwargs) -> None:  # noqa: ARG001
    from django.contrib.auth import get_user_model

    from activitylog.models import LoginEvent
    from activitylog.tasks.log_tasks import dispatch_log_task

    request = set_local_details()
    if request is None:
        return

    meta = _request_meta(request)
    geo = get_geo_data(meta["remote_ip"])
    username_field = get_user_model().USERNAME_FIELD

    try:
        dispatch_log_task(
            "login",
            {
                "login_type": LoginEvent.FAILED,
                "username": credentials.get(username_field, ""),
                **meta,
                **geo,
            },
        )
    except Exception:
        logger.exception("auth_signals.user_login_failed failed")
        if should_propagate_exceptions():
            raise


if WATCH_AUTH_EVENTS:
    signals.user_logged_in.connect(user_logged_in, dispatch_uid="activity_log_signals_logged_in")
    signals.user_logged_out.connect(user_logged_out, dispatch_uid="activity_log_signals_logged_out")
    signals.user_login_failed.connect(
        user_login_failed, dispatch_uid="activity_log_signals_login_failed"
    )
