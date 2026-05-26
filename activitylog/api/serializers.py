"""DRF serializers for all activity log models."""

from __future__ import annotations

from rest_framework import serializers

from activitylog.models import (
    CorsEvent,
    CRUDEvent,
    DatabaseConfig,
    LoginEvent,
    RequestEvent,
    RetentionPolicy,
    SystemEvent,
)

# ---------------------------------------------------------------------------
# Shared geo mixin
# ---------------------------------------------------------------------------

class _GeoMixin(serializers.ModelSerializer):
    geo = serializers.SerializerMethodField()

    def get_geo(self, obj) -> dict:
        return {
            "latitude": obj.latitude,
            "longitude": obj.longitude,
            "city": obj.city,
            "country": obj.country,
            "country_code": obj.country_code,
        }


# ---------------------------------------------------------------------------
# Event serializers
# ---------------------------------------------------------------------------

class CRUDEventSerializer(_GeoMixin):
    event_type_display = serializers.CharField(source="get_event_type_display", read_only=True)
    is_tampered = serializers.SerializerMethodField()

    def get_is_tampered(self, obj) -> bool:
        if not obj.integrity_hash:
            return False
        return not obj.verify_integrity()

    class Meta:
        model = CRUDEvent
        fields = [
            "id", "event_type", "event_type_display",
            "object_id", "content_type", "object_repr", "object_json_repr",
            "changed_fields",
            "user", "user_pk_as_string",
            "remote_ip", "browser", "platform", "operating_system", "user_agent",
            "geo", "extra_data",
            "integrity_hash", "is_tampered",
            "datetime",
        ]
        read_only_fields = fields


class LoginEventSerializer(_GeoMixin):
    login_type_display = serializers.CharField(source="get_login_type_display", read_only=True)
    is_tampered = serializers.SerializerMethodField()

    def get_is_tampered(self, obj) -> bool:
        if not obj.integrity_hash:
            return False
        return not obj.verify_integrity()

    class Meta:
        model = LoginEvent
        fields = [
            "id", "login_type", "login_type_display",
            "username", "user", "session_key",
            "remote_ip", "browser", "platform", "operating_system", "user_agent",
            "geo", "extra_data",
            "integrity_hash", "is_tampered",
            "datetime",
        ]
        read_only_fields = fields


class RequestEventSerializer(_GeoMixin):
    is_tampered = serializers.SerializerMethodField()

    def get_is_tampered(self, obj) -> bool:
        if not obj.integrity_hash:
            return False
        return not obj.verify_integrity()

    class Meta:
        model = RequestEvent
        fields = [
            "id", "url", "method", "query_string",
            "response_status", "response_time_ms",
            "request_body_size", "response_body_size",
            "user",
            "remote_ip", "browser", "platform", "operating_system", "user_agent",
            "geo", "extra_data",
            "integrity_hash", "is_tampered",
            "datetime",
        ]
        read_only_fields = fields


class CorsEventSerializer(_GeoMixin):
    is_tampered = serializers.SerializerMethodField()

    def get_is_tampered(self, obj) -> bool:
        if not obj.integrity_hash:
            return False
        return not obj.verify_integrity()

    class Meta:
        model = CorsEvent  # noqa: F821 – alias handled below
        fields = [
            "id", "url", "method", "query_string", "origin", "allowed",
            "user",
            "remote_ip", "browser", "platform", "operating_system", "user_agent",
            "geo", "extra_data",
            "integrity_hash", "is_tampered",
            "datetime",
        ]
        read_only_fields = fields


# Patch the incorrect class reference above ─ use the real model
CorsEventSerializer.Meta.model = CorsEvent  # type: ignore[attr-defined]


class SystemEventSerializer(_GeoMixin):
    is_tampered = serializers.SerializerMethodField()

    def get_is_tampered(self, obj) -> bool:
        if not obj.integrity_hash:
            return False
        return not obj.verify_integrity()

    class Meta:
        model = SystemEvent
        fields = [
            "id", "event_name", "severity", "category",
            "message", "source", "traceback",
            "user",
            "remote_ip", "extra_data",
            "geo",
            "integrity_hash", "is_tampered",
            "datetime",
        ]
        read_only_fields = fields


# ---------------------------------------------------------------------------
# DatabaseConfig serializer
# ---------------------------------------------------------------------------

class DatabaseConfigSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = DatabaseConfig
        fields = [
            "id", "name", "engine",
            "host", "port", "database_name", "username", "password",
            "route_for", "is_primary", "is_active", "is_readonly",
            "tenant_id", "connection_options",
            "last_health_check", "is_healthy", "health_error",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "last_health_check", "is_healthy", "health_error",
                            "created_at", "updated_at"]

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        instance = super().create(validated_data)
        if password is not None:
            instance.password = password
            instance.save(update_fields=["_password"])
        return instance

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        instance = super().update(instance, validated_data)
        if password is not None:
            instance.password = password
            instance.save(update_fields=["_password"])
        return instance


# ---------------------------------------------------------------------------
# RetentionPolicy serializer
# ---------------------------------------------------------------------------

class RetentionPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = RetentionPolicy
        fields = [
            "id", "name", "event_type", "retain_days",
            "is_active", "tenant_id",
            "last_run", "records_deleted",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "last_run", "records_deleted", "created_at", "updated_at"]


# ---------------------------------------------------------------------------
# Dashboard / aggregate serializer
# ---------------------------------------------------------------------------

class ActivitySummarySerializer(serializers.Serializer):
    period = serializers.CharField()
    crud_events = serializers.IntegerField()
    login_events = serializers.IntegerField()
    request_events = serializers.IntegerField()
    cors_events = serializers.IntegerField()
    system_events = serializers.IntegerField()
    failed_logins = serializers.IntegerField()
    unique_ips = serializers.IntegerField()
    top_users = serializers.ListField(child=serializers.DictField())
    top_urls = serializers.ListField(child=serializers.DictField())
    error_rate = serializers.FloatField()
