"""django-filter FilterSets for all activity log models."""

from __future__ import annotations

from django.utils import timezone

_FILTER_AVAILABLE = False
try:
    import django_filters

    _FILTER_AVAILABLE = True
except ImportError:
    pass

if _FILTER_AVAILABLE:
    from activitylog.models import (
        CorsEvent,
        CRUDEvent,
        DatabaseConfig,
        LoginEvent,
        RequestEvent,
        RetentionPolicy,
        SystemEvent,
    )

    class DateRangeFilter(django_filters.FilterSet):
        """Mixin that adds ``date_from`` / ``date_to`` filters on ``datetime``."""

        date_from = django_filters.IsoDateTimeFilter(field_name="datetime", lookup_expr="gte")
        date_to = django_filters.IsoDateTimeFilter(field_name="datetime", lookup_expr="lte")
        last_hours = django_filters.NumberFilter(method="_filter_last_hours", label="Last N hours")

        def _filter_last_hours(self, queryset, name, value):  # noqa: ARG002
            since = timezone.now() - timezone.timedelta(hours=float(value))
            return queryset.filter(datetime__gte=since)

    class CRUDEventFilter(DateRangeFilter):
        class Meta:
            model = CRUDEvent
            fields = {
                "event_type": ["exact", "in"],
                "object_id": ["exact", "icontains"],
                "content_type": ["exact"],
                "user": ["exact"],
                "remote_ip": ["exact", "icontains"],
                "country": ["exact", "icontains"],
                "city": ["exact", "icontains"],
            }

    class LoginEventFilter(DateRangeFilter):
        class Meta:
            model = LoginEvent
            fields = {
                "login_type": ["exact", "in"],
                "username": ["exact", "icontains"],
                "user": ["exact"],
                "remote_ip": ["exact", "icontains"],
                "country": ["exact"],
            }

    class RequestEventFilter(DateRangeFilter):
        class Meta:
            model = RequestEvent
            fields = {
                "method": ["exact", "in"],
                "url": ["icontains"],
                "response_status": ["exact", "in", "gte", "lte"],
                "user": ["exact"],
                "remote_ip": ["exact", "icontains"],
            }

    class CorsEventFilter(DateRangeFilter):
        class Meta:
            model = CorsEvent
            fields = {
                "method": ["exact", "in"],
                "url": ["icontains"],
                "origin": ["exact", "icontains"],
                "allowed": ["exact"],
                "user": ["exact"],
            }

    class SystemEventFilter(DateRangeFilter):
        class Meta:
            model = SystemEvent
            fields = {
                "severity": ["exact", "in"],
                "category": ["exact", "in"],
                "event_name": ["exact", "icontains"],
                "source": ["icontains"],
            }

    class DatabaseConfigFilter(django_filters.FilterSet):
        class Meta:
            model = DatabaseConfig
            fields = {
                "engine": ["exact", "in"],
                "is_active": ["exact"],
                "is_primary": ["exact"],
                "route_for": ["exact"],
                "tenant_id": ["exact"],
            }

    class RetentionPolicyFilter(django_filters.FilterSet):
        class Meta:
            model = RetentionPolicy
            fields = {
                "event_type": ["exact"],
                "is_active": ["exact"],
                "tenant_id": ["exact"],
            }

else:
    # Stub classes when django-filter is not installed
    class _StubFilter:
        pass

    CRUDEventFilter = LoginEventFilter = RequestEventFilter = _StubFilter  # type: ignore[misc,assignment]
    CorsEventFilter = SystemEventFilter = DatabaseConfigFilter = _StubFilter  # type: ignore[misc,assignment]
    RetentionPolicyFilter = _StubFilter  # type: ignore[misc,assignment]
