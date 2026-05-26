"""DRF ViewSets and API views for the activity log system."""

from __future__ import annotations

import csv
import json
import logging
from datetime import timedelta

from django.db.models import Count
from django.http import HttpResponse, StreamingHttpResponse
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from activitylog.api.filters import (
    CorsEventFilter,
    CRUDEventFilter,
    DatabaseConfigFilter,
    LoginEventFilter,
    RequestEventFilter,
    RetentionPolicyFilter,
    SystemEventFilter,
)
from activitylog.api.permissions import (
    DatabaseConfigPermission,
    IsActivityLogAdmin,
    IsActivityLogViewer,
)
from activitylog.api.serializers import (
    ActivitySummarySerializer,
    CorsEventSerializer,
    CRUDEventSerializer,
    DatabaseConfigSerializer,
    LoginEventSerializer,
    RequestEventSerializer,
    RetentionPolicySerializer,
    SystemEventSerializer,
)
from activitylog.models import (
    CorsEvent,
    CRUDEvent,
    DatabaseConfig,
    LoginEvent,
    RequestEvent,
    RetentionPolicy,
    SystemEvent,
)

logger = logging.getLogger(__name__)

_FILTER_BACKEND_CLASSES = []
try:
    from django_filters.rest_framework import DjangoFilterBackend
    _FILTER_BACKEND_CLASSES.append(DjangoFilterBackend)
except ImportError:
    pass

try:
    from rest_framework.filters import OrderingFilter, SearchFilter
    _FILTER_BACKEND_CLASSES += [SearchFilter, OrderingFilter]
except ImportError:
    pass


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------

class ActivityLogPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 1000


# ---------------------------------------------------------------------------
# Shared ViewSet mixin
# ---------------------------------------------------------------------------

class _ActivityLogViewSetMixin(viewsets.ReadOnlyModelViewSet):
    pagination_class = ActivityLogPagination
    permission_classes = [IsActivityLogViewer]
    filter_backends = _FILTER_BACKEND_CLASSES
    ordering = ["-datetime"]

    @action(detail=False, methods=["get"], url_path="export/csv")
    def export_csv(self, request):
        """Stream a CSV export of the current filtered queryset."""
        qs = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(qs, many=True)
        data = serializer.data

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = (
            f'attachment; filename="{self.model.__name__.lower()}_export.csv"'
        )

        if not data:
            return response

        writer = csv.DictWriter(response, fieldnames=list(data[0].keys()))
        writer.writeheader()
        for row in data:
            writer.writerow({k: str(v) for k, v in row.items()})
        return response

    @action(detail=False, methods=["get"], url_path="export/json")
    def export_json(self, request):
        """Return a JSON file of the current filtered queryset."""
        qs = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(qs, many=True)
        content = json.dumps(serializer.data, indent=2, default=str)
        response = HttpResponse(content, content_type="application/json")
        response["Content-Disposition"] = (
            f'attachment; filename="{self.model.__name__.lower()}_export.json"'
        )
        return response

    @action(detail=True, methods=["get"], url_path="verify-integrity")
    def verify_integrity(self, request, pk=None):
        """Verify the integrity hash of a single log entry."""
        obj = self.get_object()
        if not obj.integrity_hash:
            return Response({"status": "no_hash", "valid": None})
        valid = obj.verify_integrity()
        return Response({"status": "ok" if valid else "tampered", "valid": valid})


# ---------------------------------------------------------------------------
# CRUDEvent
# ---------------------------------------------------------------------------

class CRUDEventViewSet(_ActivityLogViewSetMixin):
    model = CRUDEvent
    queryset = CRUDEvent.objects.select_related("content_type", "user").all()
    serializer_class = CRUDEventSerializer
    filterset_class = CRUDEventFilter
    search_fields = ["object_id", "object_json_repr", "object_repr", "user__username"]
    ordering_fields = ["datetime", "event_type", "object_id"]


# ---------------------------------------------------------------------------
# LoginEvent
# ---------------------------------------------------------------------------

class LoginEventViewSet(_ActivityLogViewSetMixin):
    model = LoginEvent
    queryset = LoginEvent.objects.select_related("user").all()
    serializer_class = LoginEventSerializer
    filterset_class = LoginEventFilter
    search_fields = ["username", "remote_ip", "user__username"]
    ordering_fields = ["datetime", "login_type", "username"]

    @action(detail=False, methods=["get"], url_path="failed-logins")
    def failed_logins(self, request):
        """Quick filter for failed login attempts."""
        qs = self.filter_queryset(
            self.get_queryset().filter(login_type=LoginEvent.FAILED)
        )
        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(self.get_serializer(page, many=True).data)
        return Response(self.get_serializer(qs, many=True).data)

    @action(detail=False, methods=["get"], url_path="brute-force-suspects")
    def brute_force_suspects(self, request):
        """IPs with 5+ failed logins in the last hour."""
        since = timezone.now() - timedelta(hours=1)
        suspects = (
            LoginEvent.objects
            .filter(login_type=LoginEvent.FAILED, datetime__gte=since)
            .values("remote_ip")
            .annotate(attempts=Count("id"))
            .filter(attempts__gte=5)
            .order_by("-attempts")
        )
        return Response(list(suspects))


# ---------------------------------------------------------------------------
# RequestEvent
# ---------------------------------------------------------------------------

class RequestEventViewSet(_ActivityLogViewSetMixin):
    model = RequestEvent
    queryset = RequestEvent.objects.select_related("user").all()
    serializer_class = RequestEventSerializer
    filterset_class = RequestEventFilter
    search_fields = ["url", "remote_ip", "user__username", "query_string"]
    ordering_fields = ["datetime", "method", "response_status", "response_time_ms"]

    @action(detail=False, methods=["get"], url_path="slow-requests")
    def slow_requests(self, request):
        """Requests slower than ``threshold_ms`` (default 1000 ms)."""
        threshold = float(request.query_params.get("threshold_ms", 1000))
        qs = self.filter_queryset(
            self.get_queryset().filter(response_time_ms__gte=threshold)
        )
        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(self.get_serializer(page, many=True).data)
        return Response(self.get_serializer(qs, many=True).data)

    @action(detail=False, methods=["get"], url_path="error-rates")
    def error_rates(self, request):
        """Aggregate 4xx/5xx counts per URL for the last 24 h."""
        since = timezone.now() - timedelta(hours=24)
        data = (
            RequestEvent.objects
            .filter(datetime__gte=since, response_status__gte=400)
            .values("url", "response_status")
            .annotate(count=Count("id"))
            .order_by("-count")[:50]
        )
        return Response(list(data))


# ---------------------------------------------------------------------------
# CorsEvent
# ---------------------------------------------------------------------------

class CorsEventViewSet(_ActivityLogViewSetMixin):
    model = CorsEvent  # patched below
    queryset = CorsEvent.objects.select_related("user").all()  # patched below
    serializer_class = CorsEventSerializer
    filterset_class = CorsEventFilter
    search_fields = ["url", "origin", "remote_ip"]
    ordering_fields = ["datetime", "method", "allowed"]


# Patch class references that can't reference CorsEvent directly at definition time
CorsEventViewSet.model = CorsEvent  # type: ignore[attr-defined]
CorsEventViewSet.queryset = CorsEvent.objects.select_related("user").all()  # type: ignore[attr-defined]
CorsEventViewSet.filterset_class = CorsEventFilter  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# SystemEvent
# ---------------------------------------------------------------------------

class SystemEventViewSet(_ActivityLogViewSetMixin):
    model = SystemEvent
    queryset = SystemEvent.objects.select_related("user").all()
    serializer_class = SystemEventSerializer
    filterset_class = SystemEventFilter
    search_fields = ["event_name", "message", "source"]
    ordering_fields = ["datetime", "severity", "category"]

    @action(detail=False, methods=["get"], url_path="critical")
    def critical_events(self, request):
        since = timezone.now() - timedelta(hours=24)
        qs = self.filter_queryset(
            self.get_queryset().filter(
                severity__in=[SystemEvent.ERROR, SystemEvent.CRITICAL],
                datetime__gte=since,
            )
        )
        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(self.get_serializer(page, many=True).data)
        return Response(self.get_serializer(qs, many=True).data)


# ---------------------------------------------------------------------------
# DatabaseConfig (admin only)
# ---------------------------------------------------------------------------

class DatabaseConfigViewSet(viewsets.ModelViewSet):
    queryset = DatabaseConfig.objects.all()
    serializer_class = DatabaseConfigSerializer
    permission_classes = [DatabaseConfigPermission]
    filterset_class = DatabaseConfigFilter
    filter_backends = _FILTER_BACKEND_CLASSES
    pagination_class = ActivityLogPagination
    ordering = ["-is_primary", "name"]

    @action(detail=True, methods=["post"], url_path="health-check")
    def health_check(self, request, pk=None):
        """Trigger an immediate health check for this database config."""
        from activitylog.health.monitors import DatabaseHealthMonitor
        cfg = self.get_object()
        monitor = DatabaseHealthMonitor()
        result = monitor.check_single(cfg)
        return Response(result)

    @action(detail=True, methods=["post"], url_path="test-connection")
    def test_connection(self, request, pk=None):
        """Test a connection without saving the config (use request body)."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        from activitylog.health.monitors import DatabaseHealthMonitor
        monitor = DatabaseHealthMonitor()
        cfg = DatabaseConfig(**serializer.validated_data)
        result = monitor.check_single(cfg, save=False)
        return Response(result)


# ---------------------------------------------------------------------------
# RetentionPolicy
# ---------------------------------------------------------------------------

class RetentionPolicyViewSet(viewsets.ModelViewSet):
    queryset = RetentionPolicy.objects.all()
    serializer_class = RetentionPolicySerializer
    permission_classes = [IsActivityLogAdmin]
    filterset_class = RetentionPolicyFilter
    filter_backends = _FILTER_BACKEND_CLASSES
    pagination_class = ActivityLogPagination

    @action(detail=True, methods=["post"], url_path="run-now")
    def run_now(self, request, pk=None):
        """Execute this retention policy immediately (async if Celery available)."""
        from activitylog.tasks.retention_tasks import cleanup_old_logs
        policy = self.get_object()
        count = cleanup_old_logs(event_type=policy.event_type, days=policy.retain_days)
        return Response({"deleted": count})


# ---------------------------------------------------------------------------
# Dashboard / Analytics
# ---------------------------------------------------------------------------

class ActivityDashboardView(APIView):
    permission_classes = [IsActivityLogViewer]

    def get(self, request):
        hours = int(request.query_params.get("hours", 24))
        since = timezone.now() - timedelta(hours=hours)

        crud_count = CRUDEvent.objects.filter(datetime__gte=since).count()
        login_count = LoginEvent.objects.filter(datetime__gte=since).count()
        request_count = RequestEvent.objects.filter(datetime__gte=since).count()
        cors_count = CorsEvent.objects.filter(datetime__gte=since).count()
        system_count = SystemEvent.objects.filter(datetime__gte=since).count()
        failed_logins = LoginEvent.objects.filter(
            datetime__gte=since, login_type=LoginEvent.FAILED
        ).count()

        unique_ips = (
            RequestEvent.objects
            .filter(datetime__gte=since)
            .exclude(remote_ip__isnull=True)
            .values("remote_ip")
            .distinct()
            .count()
        )

        top_users = list(
            RequestEvent.objects
            .filter(datetime__gte=since)
            .exclude(user__isnull=True)
            .values("user__username")
            .annotate(count=Count("id"))
            .order_by("-count")[:10]
        )

        top_urls = list(
            RequestEvent.objects
            .filter(datetime__gte=since)
            .values("url")
            .annotate(count=Count("id"))
            .order_by("-count")[:10]
        )

        total_requests = request_count or 1
        error_requests = RequestEvent.objects.filter(
            datetime__gte=since, response_status__gte=400
        ).count()
        error_rate = round(error_requests / total_requests * 100, 2)

        payload = {
            "period": f"last_{hours}h",
            "crud_events": crud_count,
            "login_events": login_count,
            "request_events": request_count,
            "cors_events": cors_count,
            "system_events": system_count,
            "failed_logins": failed_logins,
            "unique_ips": unique_ips,
            "top_users": top_users,
            "top_urls": top_urls,
            "error_rate": error_rate,
        }
        return Response(ActivitySummarySerializer(payload).data)


# ---------------------------------------------------------------------------
# SSE real-time endpoint
# ---------------------------------------------------------------------------

class ActivitySSEView(APIView):
    """Server-Sent Events endpoint for real-time log streaming.

    Clients connect and receive ``data: {...}`` payloads for each new event.
    Requires Redis (or another Channels layer) and
    ``ACTIVITYLOG_REALTIME_ENABLED = True`` in settings.
    Falls back to an empty stream if Channels is not available.
    """

    permission_classes = [IsActivityLogViewer]

    def get(self, request):
        def event_stream():
            try:
                from channels.layers import get_channel_layer

                layer = get_channel_layer()
                if layer is None:
                    yield "data: {\"error\": \"channel layer not configured\"}\n\n"
                    return

                # Subscribe to the activitylog group via a one-shot listener
                yield "data: {\"status\": \"connected\"}\n\n"

                # Simple polling fallback — real Channels consumers use WebSockets
                import time
                last_ids: dict = {}
                models_map = {
                    "crud": CRUDEvent,
                    "login": LoginEvent,
                    "request": RequestEvent,
                    "system": SystemEvent,
                }

                for _ in range(300):  # max ~5 min connection
                    for etype, model in models_map.items():
                        last_id = last_ids.get(etype)
                        qs = model.objects.order_by("-datetime")[:5]
                        for obj in qs:
                            sid = str(obj.id)
                            if sid != last_id:
                                last_ids[etype] = sid
                                payload = json.dumps({
                                    "type": etype,
                                    "id": sid,
                                    "datetime": str(obj.datetime),
                                })
                                yield f"data: {payload}\n\n"
                    time.sleep(1)

            except GeneratorExit:
                pass
            except Exception as exc:
                yield f"data: {{\"error\": \"{exc}\"}}\n\n"

        response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response
