"""Migration 0002: add new fields to existing event tables, and create
SystemEvent, DatabaseConfig, RetentionPolicy models."""

from __future__ import annotations

import uuid

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("activitylog", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ------------------------------------------------------------------
        # CRUDEvent — new fields
        # ------------------------------------------------------------------
        migrations.AddField(
            model_name="crudevent",
            name="country_code",
            field=models.CharField(blank=True, max_length=10, null=True,
                                   verbose_name="Country code"),
        ),
        migrations.AddField(
            model_name="crudevent",
            name="user_agent",
            field=models.TextField(blank=True, null=True, verbose_name="User agent"),
        ),
        migrations.AddField(
            model_name="crudevent",
            name="integrity_hash",
            field=models.CharField(blank=True, editable=False, max_length=64, null=True,
                                   verbose_name="Integrity hash"),
        ),
        migrations.AddField(
            model_name="crudevent",
            name="extra_data",
            field=models.JSONField(blank=True, null=True, verbose_name="Extra data"),
        ),
        # ------------------------------------------------------------------
        # LoginEvent — new fields
        # ------------------------------------------------------------------
        migrations.AddField(
            model_name="loginevent",
            name="country_code",
            field=models.CharField(blank=True, max_length=10, null=True,
                                   verbose_name="Country code"),
        ),
        migrations.AddField(
            model_name="loginevent",
            name="user_agent",
            field=models.TextField(blank=True, null=True, verbose_name="User agent"),
        ),
        migrations.AddField(
            model_name="loginevent",
            name="session_key",
            field=models.CharField(blank=True, max_length=255, null=True,
                                   verbose_name="Session key"),
        ),
        migrations.AddField(
            model_name="loginevent",
            name="integrity_hash",
            field=models.CharField(blank=True, editable=False, max_length=64, null=True,
                                   verbose_name="Integrity hash"),
        ),
        migrations.AddField(
            model_name="loginevent",
            name="extra_data",
            field=models.JSONField(blank=True, null=True, verbose_name="Extra data"),
        ),
        # ------------------------------------------------------------------
        # RequestEvent — new fields
        # ------------------------------------------------------------------
        migrations.AddField(
            model_name="requestevent",
            name="country_code",
            field=models.CharField(blank=True, max_length=10, null=True,
                                   verbose_name="Country code"),
        ),
        migrations.AddField(
            model_name="requestevent",
            name="user_agent",
            field=models.TextField(blank=True, null=True, verbose_name="User agent"),
        ),
        migrations.AddField(
            model_name="requestevent",
            name="response_status",
            field=models.SmallIntegerField(blank=True, db_index=True, null=True,
                                           verbose_name="Response status"),
        ),
        migrations.AddField(
            model_name="requestevent",
            name="response_time_ms",
            field=models.FloatField(blank=True, null=True,
                                    verbose_name="Response time (ms)"),
        ),
        migrations.AddField(
            model_name="requestevent",
            name="request_body_size",
            field=models.BigIntegerField(blank=True, null=True,
                                         verbose_name="Request body size"),
        ),
        migrations.AddField(
            model_name="requestevent",
            name="response_body_size",
            field=models.BigIntegerField(blank=True, null=True,
                                         verbose_name="Response body size"),
        ),
        migrations.AddField(
            model_name="requestevent",
            name="integrity_hash",
            field=models.CharField(blank=True, editable=False, max_length=64, null=True,
                                   verbose_name="Integrity hash"),
        ),
        migrations.AddField(
            model_name="requestevent",
            name="extra_data",
            field=models.JSONField(blank=True, null=True, verbose_name="Extra data"),
        ),
        # ------------------------------------------------------------------
        # CorsEvent — new fields
        # ------------------------------------------------------------------
        migrations.AddField(
            model_name="corsevent",
            name="country_code",
            field=models.CharField(blank=True, max_length=10, null=True,
                                   verbose_name="Country code"),
        ),
        migrations.AddField(
            model_name="corsevent",
            name="user_agent",
            field=models.TextField(blank=True, null=True, verbose_name="User agent"),
        ),
        migrations.AddField(
            model_name="corsevent",
            name="origin",
            field=models.CharField(blank=True, db_index=True, max_length=512, null=True,
                                   verbose_name="Origin"),
        ),
        migrations.AddField(
            model_name="corsevent",
            name="allowed",
            field=models.BooleanField(null=True, verbose_name="Allowed"),
        ),
        migrations.AddField(
            model_name="corsevent",
            name="integrity_hash",
            field=models.CharField(blank=True, editable=False, max_length=64, null=True,
                                   verbose_name="Integrity hash"),
        ),
        migrations.AddField(
            model_name="corsevent",
            name="extra_data",
            field=models.JSONField(blank=True, null=True, verbose_name="Extra data"),
        ),
        # ------------------------------------------------------------------
        # New model: SystemEvent
        # ------------------------------------------------------------------
        migrations.CreateModel(
            name="SystemEvent",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False,
                                        primary_key=True, serialize=False)),
                ("browser", models.TextField(blank=True, null=True, verbose_name="Browser")),
                ("platform", models.TextField(blank=True, null=True, verbose_name="Platform")),
                ("operating_system", models.TextField(blank=True, null=True,
                                                       verbose_name="Operating system")),
                ("user_agent", models.TextField(blank=True, null=True, verbose_name="User agent")),
                ("latitude", models.CharField(blank=True, max_length=50, null=True,
                                              verbose_name="Latitude")),
                ("longitude", models.CharField(blank=True, max_length=50, null=True,
                                               verbose_name="Longitude")),
                ("city", models.CharField(blank=True, max_length=255, null=True,
                                          verbose_name="City")),
                ("country", models.CharField(blank=True, max_length=255, null=True,
                                             verbose_name="Country")),
                ("country_code", models.CharField(blank=True, max_length=10, null=True,
                                                  verbose_name="Country code")),
                ("remote_ip", models.CharField(blank=True, db_index=True, max_length=50,
                                               null=True, verbose_name="Remote IP")),
                ("integrity_hash", models.CharField(blank=True, editable=False, max_length=64,
                                                    null=True, verbose_name="Integrity hash")),
                ("extra_data", models.JSONField(blank=True, null=True, verbose_name="Extra data")),
                ("datetime", models.DateTimeField(db_index=True,
                                                  default=django.utils.timezone.now,
                                                  verbose_name="Date time")),
                ("event_name", models.CharField(db_index=True, max_length=255,
                                                verbose_name="Event name")),
                ("severity", models.CharField(
                    choices=[("INFO", "Info"), ("WARNING", "Warning"),
                             ("ERROR", "Error"), ("CRITICAL", "Critical")],
                    db_index=True, default="INFO", max_length=20, verbose_name="Severity")),
                ("category", models.CharField(
                    choices=[("server", "Server"), ("security", "Security"),
                             ("database", "Database"), ("celery", "Celery"),
                             ("custom", "Custom")],
                    db_index=True, default="custom", max_length=50, verbose_name="Category")),
                ("message", models.TextField(verbose_name="Message")),
                ("source", models.CharField(blank=True, max_length=512, null=True,
                                            verbose_name="Source")),
                ("traceback", models.TextField(blank=True, null=True, verbose_name="Traceback")),
                ("user", models.ForeignKey(
                    blank=True, db_constraint=False, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    to=settings.AUTH_USER_MODEL, verbose_name="User")),
            ],
            options={
                "verbose_name": "System event",
                "verbose_name_plural": "System events",
                "ordering": ["-datetime"],
            },
        ),
        migrations.AddIndex(
            model_name="systemevent",
            index=models.Index(fields=["severity", "datetime"], name="actlog_sev_dt_idx"),
        ),
        migrations.AddIndex(
            model_name="systemevent",
            index=models.Index(fields=["category", "datetime"], name="actlog_cat_dt_idx"),
        ),
        # ------------------------------------------------------------------
        # New model: DatabaseConfig
        # ------------------------------------------------------------------
        migrations.CreateModel(
            name="DatabaseConfig",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False,
                                        primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=255, unique=True, verbose_name="Name")),
                ("engine", models.CharField(
                    choices=[("postgresql", "PostgreSQL"), ("mysql", "MySQL"),
                             ("sqlite", "SQLite"), ("clickhouse", "ClickHouse"),
                             ("mongodb", "MongoDB"), ("scylladb", "ScyllaDB / Cassandra")],
                    max_length=50, verbose_name="Engine")),
                ("host", models.CharField(max_length=512, verbose_name="Host")),
                ("port", models.PositiveIntegerField(blank=True, null=True, verbose_name="Port")),
                ("database_name", models.CharField(max_length=255,
                                                   verbose_name="Database name")),
                ("username", models.CharField(blank=True, max_length=255, null=True,
                                              verbose_name="Username")),
                ("password", models.TextField(blank=True, db_column="password", null=True,
                                              verbose_name="Password (encrypted)")),
                ("route_for", models.CharField(
                    choices=[("all", "All events"), ("crud", "CRUD events only"),
                             ("auth", "Auth/login events only"),
                             ("request", "Request events only"),
                             ("system", "System events only"),
                             ("analytics", "Analytics / high-volume")],
                    default="all", max_length=20, verbose_name="Route for")),
                ("is_primary", models.BooleanField(default=False, verbose_name="Is primary")),
                ("is_active", models.BooleanField(db_index=True, default=True,
                                                  verbose_name="Is active")),
                ("is_readonly", models.BooleanField(default=False, verbose_name="Read only")),
                ("tenant_id", models.CharField(blank=True, db_index=True, max_length=255,
                                               null=True, verbose_name="Tenant ID")),
                ("connection_options", models.JSONField(blank=True, default=dict,
                                                        verbose_name="Connection options")),
                ("last_health_check", models.DateTimeField(blank=True, null=True,
                                                           verbose_name="Last health check")),
                ("is_healthy", models.BooleanField(null=True, verbose_name="Is healthy")),
                ("health_error", models.TextField(blank=True, null=True,
                                                  verbose_name="Health error")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Database configuration",
                "verbose_name_plural": "Database configurations",
                "ordering": ["-is_primary", "name"],
            },
        ),
        # ------------------------------------------------------------------
        # New model: RetentionPolicy
        # ------------------------------------------------------------------
        migrations.CreateModel(
            name="RetentionPolicy",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False,
                                        primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=255, unique=True, verbose_name="Name")),
                ("event_type", models.CharField(
                    choices=[("crud", "CRUD events"), ("login", "Login events"),
                             ("request", "Request events"), ("cors", "CORS events"),
                             ("system", "System events"), ("all", "All events")],
                    default="all", max_length=20, verbose_name="Event type")),
                ("retain_days", models.PositiveIntegerField(verbose_name="Retain for (days)")),
                ("is_active", models.BooleanField(default=True, verbose_name="Is active")),
                ("tenant_id", models.CharField(blank=True, db_index=True, max_length=255,
                                               null=True, verbose_name="Tenant ID")),
                ("last_run", models.DateTimeField(blank=True, null=True,
                                                  verbose_name="Last run")),
                ("records_deleted", models.BigIntegerField(default=0,
                                                           verbose_name="Records deleted (total)")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Retention policy",
                "verbose_name_plural": "Retention policies",
            },
        ),
        # ------------------------------------------------------------------
        # Indexes on updated models
        # ------------------------------------------------------------------
        migrations.AddIndex(
            model_name="crudevent",
            index=models.Index(fields=["user", "datetime"], name="actlog_crud_user_dt_idx"),
        ),
        migrations.AddIndex(
            model_name="crudevent",
            index=models.Index(fields=["event_type", "datetime"],
                               name="actlog_crud_evtype_dt_idx"),
        ),
        migrations.AddIndex(
            model_name="loginevent",
            index=models.Index(fields=["login_type", "datetime"],
                               name="actlog_login_type_dt_idx"),
        ),
        migrations.AddIndex(
            model_name="loginevent",
            index=models.Index(fields=["user", "datetime"], name="actlog_login_user_dt_idx"),
        ),
        migrations.AddIndex(
            model_name="requestevent",
            index=models.Index(fields=["method", "datetime"], name="actlog_req_method_dt_idx"),
        ),
        migrations.AddIndex(
            model_name="requestevent",
            index=models.Index(fields=["response_status", "datetime"],
                               name="actlog_req_status_dt_idx"),
        ),
    ]
