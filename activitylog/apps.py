from __future__ import annotations

from django.apps import AppConfig


class ActivitylogConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "activitylog"
    verbose_name = "Activity Log"

    def ready(self) -> None:
        from activitylog.compat import assert_django_compatible
        assert_django_compatible()

        # Populate UNREGISTERED_CLASSES / REGISTERED_CLASSES in settings shim
        # *after* the app registry is ready so model imports are safe.
        self._resolve_class_lists()

        # Connect all signal handlers (side-effect imports only).
        for _mod in (
            "activitylog.signals.auth_signals",
            "activitylog.signals.cors_signals",
            "activitylog.signals.model_signals",
            "activitylog.signals.request_signals",
        ):
            __import__(_mod)

    @staticmethod
    def _resolve_class_lists() -> None:
        """Resolve dotted-string class references and populate the settings shim."""
        from importlib import import_module

        from django.apps import apps as django_apps
        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType
        from django.contrib.sessions.models import Session
        from django.db.migrations import Migration
        from django.db.migrations.recorder import MigrationRecorder

        import activitylog.settings as _shim
        from activitylog.conf import activitylog_settings
        from activitylog.models import (
            CorsEvent,
            CRUDEvent,
            DatabaseConfig,
            LoginEvent,
            RequestEvent,
            RetentionPolicy,
            SystemEvent,
        )

        builtin_excluded = [
            CRUDEvent, LoginEvent, RequestEvent, CorsEvent, SystemEvent,
            DatabaseConfig, RetentionPolicy,
            Migration, Session, Permission, ContentType,
            MigrationRecorder.Migration,
        ]
        if django_apps.is_installed("django.contrib.admin"):
            from django.contrib.admin.models import LogEntry
            builtin_excluded.append(LogEntry)

        # User-supplied extras (may be dotted strings)
        extras: list = list(activitylog_settings.UNREGISTERED_CLASSES_EXTRA)
        _resolve_strings(extras)

        _shim.UNREGISTERED_CLASSES = builtin_excluded + extras

        registered: list = list(activitylog_settings.REGISTERED_CLASSES)
        _resolve_strings(registered)
        _shim.REGISTERED_CLASSES = registered

        # Resolve CRUD_DIFFERENCE_CALLBACKS from strings → callables
        callbacks: list = list(activitylog_settings.CRUD_DIFFERENCE_CALLBACKS)
        for idx, cb in enumerate(callbacks):
            if not callable(cb):
                mod_path, fn_name = str(cb).rsplit(".", 1)
                callbacks[idx] = getattr(import_module(mod_path), fn_name, None)
        _shim.CRUD_DIFFERENCE_CALLBACKS = [c for c in callbacks if callable(c)]


def _resolve_strings(class_list: list) -> None:
    """Resolve any dotted-string items in *class_list* to model classes in place."""
    from django.apps import apps
    for idx, item in enumerate(class_list):
        if isinstance(item, str):
            class_list[idx] = apps.get_model(item)
