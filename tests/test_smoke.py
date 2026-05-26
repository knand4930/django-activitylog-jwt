from __future__ import annotations

import django
from activitylog.compat import DJANGO_VERSION, PYTHON_VERSION
from activitylog.conf import activitylog_settings
from django.apps import apps


def test_activitylog_app_is_installed() -> None:
    app_config = apps.get_app_config("activitylog")

    assert app_config.name == "activitylog"
    assert app_config.verbose_name == "Activity Log"


def test_runtime_versions_are_supported() -> None:
    assert django.VERSION[:3] == DJANGO_VERSION
    assert DJANGO_VERSION >= (4, 0)
    assert PYTHON_VERSION >= (3, 8)


def test_default_settings_are_available() -> None:
    assert activitylog_settings.JWT_AUTH_HEADER_PREFIX == "Bearer"
    assert activitylog_settings.DATABASE_ALIAS == "default"
    assert activitylog_settings.TRACK_RESPONSE_METRICS is True
