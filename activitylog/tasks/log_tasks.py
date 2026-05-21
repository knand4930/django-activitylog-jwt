"""Celery tasks for async activity log writing.

All signal handlers call ``dispatch_log_task()``.  If Celery is available and
configured, the write happens in a worker process.  Otherwise it falls back to
a direct synchronous save on the same thread.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Celery availability guard
# ---------------------------------------------------------------------------

_CELERY_AVAILABLE = False
try:
    from celery import shared_task
    _CELERY_AVAILABLE = True
except ImportError:
    pass


def _noop_shared_task(fn=None, **_kwargs):
    """Fallback decorator when Celery is not installed."""
    if fn is None:
        return _noop_shared_task

    def wrapper(*args, **kwargs):
        return fn(*args, **kwargs)

    wrapper.delay = lambda *a, **kw: fn(*a, **kw)
    wrapper.apply_async = lambda args=None, kwargs=None, **_: fn(*(args or []), **(kwargs or {}))
    return wrapper


if not _CELERY_AVAILABLE:
    shared_task = _noop_shared_task  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Helper: stamp integrity hash before save
# ---------------------------------------------------------------------------

def _stamp_and_save(obj) -> None:
    obj.integrity_hash = obj.compute_integrity_hash()
    obj.save()


# ---------------------------------------------------------------------------
# Individual event tasks
# ---------------------------------------------------------------------------

@shared_task(bind=True, max_retries=3, default_retry_delay=5, name="activitylog.save_crud_event")
def save_crud_event(self, data: Dict[str, Any]) -> None:
    try:
        from activitylog.models import CRUDEvent
        event = CRUDEvent(**data)
        _stamp_and_save(event)
        _broadcast_event("crud", str(event.id), data)
    except Exception as exc:
        logger.exception("save_crud_event failed: %s", exc)
        try:
            raise self.retry(exc=exc)
        except AttributeError:
            pass


@shared_task(bind=True, max_retries=3, default_retry_delay=5, name="activitylog.save_login_event")
def save_login_event(self, data: Dict[str, Any]) -> None:
    try:
        from activitylog.models import LoginEvent
        event = LoginEvent(**data)
        _stamp_and_save(event)
        _broadcast_event("login", str(event.id), data)
    except Exception as exc:
        logger.exception("save_login_event failed: %s", exc)
        try:
            raise self.retry(exc=exc)
        except AttributeError:
            pass


@shared_task(bind=True, max_retries=3, default_retry_delay=5, name="activitylog.save_request_event")
def save_request_event(self, data: Dict[str, Any]) -> None:
    try:
        from activitylog.models import RequestEvent
        event = RequestEvent(**data)
        _stamp_and_save(event)
        _broadcast_event("request", str(event.id), data)
    except Exception as exc:
        logger.exception("save_request_event failed: %s", exc)
        try:
            raise self.retry(exc=exc)
        except AttributeError:
            pass


@shared_task(bind=True, max_retries=3, default_retry_delay=5, name="activitylog.save_cors_event")
def save_cors_event(self, data: Dict[str, Any]) -> None:
    try:
        from activitylog.models import CorsEvent
        event = CorsEvent(**data)
        _stamp_and_save(event)
        _broadcast_event("cors", str(event.id), data)
    except Exception as exc:
        logger.exception("save_cors_event failed: %s", exc)
        try:
            raise self.retry(exc=exc)
        except AttributeError:
            pass


@shared_task(bind=True, max_retries=3, default_retry_delay=5, name="activitylog.save_system_event")
def save_system_event(self, data: Dict[str, Any]) -> None:
    try:
        from activitylog.models import SystemEvent
        event = SystemEvent(**data)
        _stamp_and_save(event)
        _broadcast_event("system", str(event.id), data)
    except Exception as exc:
        logger.exception("save_system_event failed: %s", exc)
        try:
            raise self.retry(exc=exc)
        except AttributeError:
            pass


# ---------------------------------------------------------------------------
# Bulk task (batched writes for high-volume scenarios)
# ---------------------------------------------------------------------------

@shared_task(bind=True, max_retries=2, name="activitylog.bulk_save_request_events")
def bulk_save_request_events(self, records: list) -> None:
    """Bulk-insert a list of request event dicts (used by Kafka/queue consumers)."""
    try:
        from activitylog.models import RequestEvent
        objs = []
        for data in records:
            obj = RequestEvent(**data)
            obj.integrity_hash = obj.compute_integrity_hash()
            objs.append(obj)
        RequestEvent.objects.bulk_create(objs, ignore_conflicts=True)
    except Exception as exc:
        logger.exception("bulk_save_request_events failed: %s", exc)
        try:
            raise self.retry(exc=exc)
        except AttributeError:
            pass


# ---------------------------------------------------------------------------
# Dispatcher: chooses async or sync path
# ---------------------------------------------------------------------------

_TASK_MAP = {
    "crud": save_crud_event,
    "login": save_login_event,
    "request": save_request_event,
    "cors": save_cors_event,
    "system": save_system_event,
}


def dispatch_log_task(event_type: str, data: Dict[str, Any], queue: Optional[str] = None) -> None:
    """Send a log-write task to Celery or run it synchronously as a fallback.

    :param event_type: One of ``"crud"``, ``"login"``, ``"request"``, ``"cors"``, ``"system"``.
    :param data: Keyword arguments to pass to the model constructor.
    :param queue: Optional Celery queue name override.
    """
    task = _TASK_MAP.get(event_type)
    if task is None:
        logger.error("dispatch_log_task: unknown event_type '%s'", event_type)
        return

    use_async = _CELERY_AVAILABLE and _celery_is_configured()
    if use_async:
        kwargs: Dict[str, Any] = {"args": [data]}
        if queue:
            kwargs["queue"] = queue
        task.apply_async(**kwargs)
    else:
        task(data)


def _celery_is_configured() -> bool:
    try:
        from django.conf import settings
        return bool(getattr(settings, "CELERY_BROKER_URL", None) or
                    getattr(settings, "BROKER_URL", None))
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Real-time broadcast (WebSocket/SSE channel layer)
# ---------------------------------------------------------------------------

def _broadcast_event(event_type: str, event_id: str, data: Dict[str, Any]) -> None:
    """Publish a new-event notification to the channel layer if available."""
    try:
        from django.conf import settings
        if not getattr(settings, "ACTIVITYLOG_REALTIME_ENABLED", False):
            return
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        layer = get_channel_layer()
        if layer is None:
            return
        async_to_sync(layer.group_send)(
            "activitylog",
            {
                "type": "log.event",
                "event_type": event_type,
                "event_id": event_id,
            },
        )
    except Exception:
        pass
