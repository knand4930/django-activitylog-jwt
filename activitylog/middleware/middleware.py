"""ActivityLog middleware: stores the current request in thread-local storage
and captures structured per-request metrics (timing, status, body sizes)."""

from __future__ import annotations

import contextlib
import logging
import time
from threading import local
from typing import Callable, Optional

logger = logging.getLogger(__name__)

_thread_locals = local()


# ---------------------------------------------------------------------------
# Thread-local accessors (used by signals)
# ---------------------------------------------------------------------------

class _MockRequest:
    def __init__(self, user=None):
        self.user = user


def get_current_request():
    return getattr(_thread_locals, "request", None)


def get_current_user():
    req = get_current_request()
    return getattr(req, "user", None) if req else None


def set_current_user(user) -> None:
    req = get_current_request()
    if req is not None:
        req.user = user
    else:
        _thread_locals.request = _MockRequest(user=user)


def clear_request() -> None:
    with contextlib.suppress(AttributeError):
        del _thread_locals.request


def set_local_details():
    return getattr(_thread_locals, "request", None)


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

class ActivityLogMiddleware:
    """Attach the current HTTP request to thread-local storage so that Django
    signals (fired during the request/response cycle) can access it without
    an explicit parameter.

    Also records structured request timing and response status for the
    RequestEvent model when ``DJANGO_ACTIVITY_LOG_WATCH_REQUEST_EVENTS`` is
    enabled.
    """

    def __init__(self, get_response: Callable) -> None:
        self.get_response = get_response
        from django.conf import settings
        self._watch_requests: bool = getattr(
            settings, "DJANGO_ACTIVITY_LOG_WATCH_REQUEST_EVENTS", True
        )
        self._track_response: bool = getattr(
            settings, "DJANGO_ACTIVITY_LOG_TRACK_RESPONSE_METRICS", True
        )

    def __call__(self, request):
        _thread_locals.request = request
        start = time.perf_counter()

        response = self.get_response(request)

        elapsed_ms = (time.perf_counter() - start) * 1000

        if self._watch_requests and self._track_response:
            self._record_response_metrics(request, response, elapsed_ms)

        with contextlib.suppress(AttributeError):
            del _thread_locals.request

        return response

    def process_exception(self, request, exception):  # noqa: ARG002
        with contextlib.suppress(AttributeError):
            del _thread_locals.request

    # ------------------------------------------------------------------

    def _record_response_metrics(self, request, response, elapsed_ms: float) -> None:
        """Back-fill response_status and response_time_ms on the last RequestEvent
        that was created for this request path.

        This runs after the view completes, so we can capture the real HTTP status.
        We do a best-effort lookup by URL + approximate timestamp.
        """
        try:
            from activitylog.models import RequestEvent
            from django.utils import timezone
            from datetime import timedelta

            # The request_started signal already created the row; update it.
            # Use a 2-second window to avoid touching the wrong row under load.
            threshold = timezone.now() - timedelta(seconds=2)

            content_length: Optional[int] = None
            with contextlib.suppress(Exception):
                content_length = int(response.get("Content-Length", 0)) or None

            req_size: Optional[int] = None
            with contextlib.suppress(Exception):
                req_size = int(request.META.get("CONTENT_LENGTH") or 0) or None

            (
                RequestEvent.objects
                .filter(
                    url=request.path_info,
                    method=request.method,
                    datetime__gte=threshold,
                    response_status__isnull=True,
                )
                .order_by("-datetime")[:1]
                .update(
                    response_status=response.status_code,
                    response_time_ms=round(elapsed_ms, 2),
                    response_body_size=content_length,
                    request_body_size=req_size,
                )
            )
        except Exception as exc:
            logger.debug("ActivityLogMiddleware: could not update response metrics: %s", exc)
