"""Django admin registrations — compatible with Django 4.2 – 6.x."""

from __future__ import annotations

import csv
import datetime

from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponse
from django.urls import reverse
from django.utils.html import escape
from django.utils.safestring import mark_safe

from activitylog.admin_helpers import ActivityLogModelAdmin, prettify_json
from activitylog.models import (
    CorsEvent,
    CRUDEvent,
    DatabaseConfig,
    LoginEvent,
    RequestEvent,
    RetentionPolicy,
    SystemEvent,
)
from activitylog.settings import (
    ADMIN_SHOW_AUTH_EVENTS,
    ADMIN_SHOW_CORS_EVENTS,
    ADMIN_SHOW_MODEL_EVENTS,
    ADMIN_SHOW_REQUEST_EVENTS,
    CORS_EVENT_LIST_FILTER,
    CORS_EVENT_SEARCH_FIELDS,
    CRUD_EVENT_LIST_FILTER,
    CRUD_EVENT_SEARCH_FIELDS,
    LOGIN_EVENT_LIST_FILTER,
    LOGIN_EVENT_SEARCH_FIELDS,
    REQUEST_EVENT_LIST_FILTER,
    REQUEST_EVENT_SEARCH_FIELDS,
)

# ---------------------------------------------------------------------------
# Shared action
# ---------------------------------------------------------------------------

@admin.action(description="Export selected rows to CSV")
def export_to_csv(modeladmin, request, queryset):
    opts = modeladmin.model._meta
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{opts.verbose_name}.csv"'
    writer = csv.writer(response)
    fields = [
        f for f in opts.get_fields()
        if not f.many_to_many and not f.one_to_many
    ]
    writer.writerow([getattr(f, "verbose_name", f.name) for f in fields])
    for obj in queryset:
        row = []
        for f in fields:
            val = getattr(obj, f.name, "")
            if isinstance(val, datetime.datetime):
                val = val.strftime("%Y-%m-%d %H:%M:%S UTC")
            row.append(val)
        writer.writerow(row)
    return response


# ---------------------------------------------------------------------------
# CRUDEvent
# ---------------------------------------------------------------------------

@admin.register(CRUDEvent)
class CRUDEventAdmin(ActivityLogModelAdmin):
    list_display = [
        "get_event_type_display",
        "get_content_type",
        "object_id",
        "object_repr_link",
        "user_link",
        "datetime",
        "remote_ip",
        "integrity_status",
    ]
    date_hierarchy = "datetime"
    list_filter = CRUD_EVENT_LIST_FILTER
    search_fields = CRUD_EVENT_SEARCH_FIELDS
    readonly_fields = [
        "id", "user", "event_type", "object_id", "get_content_type",
        "object_repr", "object_json_repr_prettified", "get_user",
        "user_pk_as_string", "browser", "platform", "operating_system",
        "user_agent", "latitude", "longitude", "city", "country",
        "country_code", "remote_ip", "datetime", "changed_fields_prettified",
        "integrity_hash", "integrity_status", "extra_data",
    ]
    exclude = ["object_json_repr", "changed_fields"]
    actions = [export_to_csv]

    def get_changelist_instance(self, *args, **kwargs):
        instance = super().get_changelist_instance(*args, **kwargs)
        ids = [obj.content_type_id for obj in instance.result_list]
        self.content_types_by_id = {
            ct.id: ct for ct in ContentType.objects.filter(id__in=ids)
        }
        return instance

    @admin.display(description="Content Type")
    def get_content_type(self, obj):
        return self.content_types_by_id.get(obj.content_type_id, "—")

    @admin.display(description="User")
    def get_user(self, obj):
        return self.users_by_id.get(obj.user_id, "—")

    @admin.display(description="Object")
    def object_repr_link(self, obj):
        if obj.event_type == CRUDEvent.DELETE:
            return escape(obj.object_repr or "")
        try:
            ct = self.content_types_by_id.get(obj.content_type_id)
            url = reverse(
                f"admin:{ct.app_label}_{ct.model}_change", args=(obj.object_id,)
            )
            return mark_safe(f'<a href="{url}">{escape(obj.object_repr or "")}</a>')  # noqa: S308
        except Exception:
            return escape(obj.object_repr or "")

    @admin.display(description="JSON repr")
    def object_json_repr_prettified(self, obj):
        return prettify_json(obj.object_json_repr)

    @admin.display(description="Changed fields")
    def changed_fields_prettified(self, obj):
        return prettify_json(obj.changed_fields)

    @admin.display(description="Integrity", boolean=True)
    def integrity_status(self, obj):
        if not obj.integrity_hash:
            return None
        return obj.verify_integrity()

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs if ADMIN_SHOW_MODEL_EVENTS else qs.none()


# ---------------------------------------------------------------------------
# LoginEvent
# ---------------------------------------------------------------------------

@admin.register(LoginEvent)
class LoginEventAdmin(ActivityLogModelAdmin):
    list_display = [
        "datetime", "get_login_type_display", "user_link",
        "username", "remote_ip", "city", "country", "integrity_status",
    ]
    date_hierarchy = "datetime"
    list_filter = LOGIN_EVENT_LIST_FILTER
    search_fields = LOGIN_EVENT_SEARCH_FIELDS
    readonly_fields = [
        "id", "username", "user", "login_type", "session_key",
        "browser", "platform", "operating_system", "user_agent",
        "latitude", "longitude", "city", "country", "country_code",
        "remote_ip", "datetime", "integrity_hash", "integrity_status", "extra_data",
    ]
    actions = [export_to_csv]

    @admin.display(description="Integrity", boolean=True)
    def integrity_status(self, obj):
        if not obj.integrity_hash:
            return None
        return obj.verify_integrity()

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs if ADMIN_SHOW_AUTH_EVENTS else qs.none()


# ---------------------------------------------------------------------------
# RequestEvent
# ---------------------------------------------------------------------------

@admin.register(RequestEvent)
class RequestEventAdmin(ActivityLogModelAdmin):
    list_display = [
        "datetime", "user_link", "method", "url",
        "response_status", "response_time_ms", "remote_ip",
    ]
    date_hierarchy = "datetime"
    list_filter = REQUEST_EVENT_LIST_FILTER
    search_fields = REQUEST_EVENT_SEARCH_FIELDS
    readonly_fields = [
        "id", "url", "method", "query_string", "response_status",
        "response_time_ms", "request_body_size", "response_body_size",
        "browser", "platform", "operating_system", "user_agent",
        "latitude", "longitude", "city", "country", "country_code",
        "remote_ip", "datetime", "integrity_hash", "extra_data",
    ]
    actions = [export_to_csv]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs if ADMIN_SHOW_REQUEST_EVENTS else qs.none()


# ---------------------------------------------------------------------------
# CorsEvent
# ---------------------------------------------------------------------------

@admin.register(CorsEvent)
class CorsEventAdmin(ActivityLogModelAdmin):
    list_display = ["datetime", "user_link", "method", "url", "origin", "allowed", "remote_ip"]
    date_hierarchy = "datetime"
    list_filter = CORS_EVENT_LIST_FILTER
    search_fields = CORS_EVENT_SEARCH_FIELDS
    readonly_fields = [
        "id", "url", "method", "query_string", "origin", "allowed",
        "browser", "platform", "operating_system", "user_agent",
        "latitude", "longitude", "city", "country", "country_code",
        "remote_ip", "datetime", "integrity_hash", "extra_data",
    ]
    actions = [export_to_csv]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs if ADMIN_SHOW_CORS_EVENTS else qs.none()


# ---------------------------------------------------------------------------
# SystemEvent
# ---------------------------------------------------------------------------

@admin.register(SystemEvent)
class SystemEventAdmin(admin.ModelAdmin):
    list_display = ["datetime", "severity", "category", "event_name", "source", "user"]
    list_filter = ["severity", "category", "datetime"]
    search_fields = ["event_name", "message", "source"]
    date_hierarchy = "datetime"
    readonly_fields = [
        "id", "event_name", "severity", "category", "message",
        "source", "traceback", "user", "remote_ip",
        "latitude", "longitude", "city", "country", "country_code",
        "integrity_hash", "extra_data", "datetime",
    ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


# ---------------------------------------------------------------------------
# DatabaseConfig
# ---------------------------------------------------------------------------

@admin.register(DatabaseConfig)
class DatabaseConfigAdmin(admin.ModelAdmin):
    list_display = [
        "name", "engine", "host", "database_name",
        "route_for", "is_primary", "is_active", "is_healthy",
        "last_health_check", "tenant_id",
    ]
    list_filter = ["engine", "route_for", "is_active", "is_primary", "is_healthy"]
    search_fields = ["name", "host", "database_name", "tenant_id"]
    readonly_fields = [
        "id", "is_healthy", "health_error", "last_health_check",
        "created_at", "updated_at",
    ]
    fieldsets = (
        (None, {"fields": ("id", "name", "engine", "route_for", "tenant_id")}),
        ("Connection", {"fields": (
            "host", "port", "database_name", "username", "_password",
            "connection_options",
        )}),
        ("Flags", {"fields": ("is_primary", "is_active", "is_readonly")}),
        ("Health", {"fields": ("is_healthy", "health_error", "last_health_check")}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


# ---------------------------------------------------------------------------
# RetentionPolicy
# ---------------------------------------------------------------------------

@admin.register(RetentionPolicy)
class RetentionPolicyAdmin(admin.ModelAdmin):
    list_display = [
        "name", "event_type", "retain_days", "is_active",
        "tenant_id", "last_run", "records_deleted",
    ]
    list_filter = ["event_type", "is_active"]
    search_fields = ["name", "tenant_id"]
    readonly_fields = ["id", "last_run", "records_deleted", "created_at", "updated_at"]
