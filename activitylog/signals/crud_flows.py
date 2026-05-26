"""CRUD signal helpers: called from model_signals.py to create CRUDEvents."""

from __future__ import annotations

import json
import logging

from django.contrib.auth.models import AnonymousUser
from django.contrib.contenttypes.models import ContentType
from django.core.serializers.json import DjangoJSONEncoder
from django.utils import timezone

from activitylog.middleware.middleware import get_current_request, get_current_user
from activitylog.models import CRUDEvent
from activitylog.settings import (
    GNOME_SHELL_SESSION_MODE,
    HTTP_SEC_CH_UA,
    HTTP_SEC_CH_UA_PLATFORM,
    REMOTE_ADDR_HEADER,
)
from activitylog.utils import get_geo_data, get_m2m_field_name, should_propagate_exceptions

logger = logging.getLogger(__name__)


def _current_user_details():
    user_id = None
    user_pk_as_string = ""
    with __import__("contextlib").suppress(Exception):
        user = get_current_user()
        if user and not isinstance(user, AnonymousUser):
            user_id = user.id
            user_pk_as_string = str(user.pk)
    return user_id, user_pk_as_string


def _request_context() -> dict:
    request = get_current_request()
    if request is None:
        return {}
    return {
        "remote_ip": request.META.get(REMOTE_ADDR_HEADER),
        "browser": request.META.get(HTTP_SEC_CH_UA),
        "platform": request.META.get(HTTP_SEC_CH_UA_PLATFORM),
        "operating_system": request.META.get(GNOME_SHELL_SESSION_MODE),
        "user_agent": request.META.get("HTTP_USER_AGENT"),
    }


def _build_event_data(event_type: int, instance, object_json_repr, **extra) -> dict:
    user_id, user_pk_as_string = _current_user_details()
    ctx = _request_context()
    remote_ip = ctx.get("remote_ip")
    geo = get_geo_data(remote_ip) if remote_ip else {}

    return {
        "content_type_id": ContentType.objects.get_for_model(instance).id,
        "datetime": timezone.now(),
        "event_type": event_type,
        "object_id": str(instance.pk),
        "object_json_repr": object_json_repr or "",
        "object_repr": str(instance),
        "user_id": user_id,
        "user_pk_as_string": user_pk_as_string,
        **ctx,
        **geo,
        **extra,
    }


def _dispatch(event_type: int, instance, object_json_repr, **extra) -> None:
    from activitylog.tasks.log_tasks import dispatch_log_task

    data = _build_event_data(event_type, instance, object_json_repr, **extra)
    dispatch_log_task("crud", data)


def _handle_exception(instance, signal_name: str) -> None:
    with __import__("contextlib").suppress(Exception):
        logger.exception(
            "CRUDEvent creation failed in %s for %s (pk=%s)",
            signal_name,
            type(instance).__name__,
            instance.pk,
        )
    if should_propagate_exceptions():
        raise


def pre_save_crud_flow(instance, object_json_repr: str, changed_fields) -> None:
    try:
        _dispatch(CRUDEvent.UPDATE, instance, object_json_repr, changed_fields=changed_fields)
    except Exception:
        _handle_exception(instance, "pre_save")


def post_save_crud_flow(instance, object_json_repr: str) -> None:
    try:
        _dispatch(CRUDEvent.CREATE, instance, object_json_repr)
    except Exception:
        _handle_exception(instance, "post_save")


def m2m_changed_crud_flow(action, model, instance, pk_set, event_type, object_json_repr) -> None:
    try:
        if action == "post_clear":
            changed_fields: object = []
        else:
            changed_fields = json.dumps(
                {get_m2m_field_name(model, instance): list(pk_set or [])},
                cls=DjangoJSONEncoder,
            )
        _dispatch(event_type, instance, object_json_repr, changed_fields=changed_fields)
    except Exception:
        _handle_exception(instance, "m2m_changed")


def post_delete_crud_flow(instance, object_json_repr: str) -> None:
    try:
        _dispatch(CRUDEvent.DELETE, instance, object_json_repr)
    except Exception:
        _handle_exception(instance, "post_delete")
