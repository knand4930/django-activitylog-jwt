import uuid
from importlib import import_module
import os
import django.db.utils
from django.apps import apps
from django.conf import settings
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.sessions.models import Session
from django.db.migrations import Migration
from django.db.migrations.recorder import MigrationRecorder

from activitylog.models import CRUDEvent, LoginEvent, RequestEvent, CorsEvent


def get_model_list(class_list):
    """Get a list of model classes from a list of strings.

    Receives a list of strings with app_name.model_name format and turns them into classes.
    If an item is already a class, it ignores it.
    """
    for idx, item in enumerate(class_list):
        if isinstance(item, (str,)):
            model_class = apps.get_model(item)
            class_list[idx] = model_class


# Should Django Activity log model/auth/request events?
WATCH_AUTH_EVENTS = getattr(settings, "DJANGO_ACTIVITY_LOG_WATCH_AUTH_EVENTS", True)
WATCH_MODEL_EVENTS = getattr(settings, "DJANGO_ACTIVITY_LOG_WATCH_MODEL_EVENTS", True)
WATCH_REQUEST_EVENTS = getattr(settings, "DJANGO_ACTIVITY_LOG_WATCH_REQUEST_EVENTS", True)
WATCH_CORS_EVENTS = getattr(settings, "DJANGO_ACTIVITY_LOG_WATCH_CORS_EVENTS", True)

X_FORWARDED_FOR = getattr(settings, "DJANGO_ACTIVITY_LOG_REMOTE_ADDR_HEADER", 'HTTP_X_FORWARDED_FOR')
if X_FORWARDED_FOR:
    REMOTE_ADDR_HEADER = X_FORWARDED_FOR.split(',')[0].strip()
else:
    REMOTE_ADDR_HEADER = getattr(settings, "DJANGO_ACTIVITY_LOG_REMOTE_ADDR_HEADER", "REMOTE_ADDR")

HTTP_SEC_CH_UA = getattr(settings, "DJANGO_ACTIVITY_LOG_BROWSER", "HTTP_SEC_CH_UA")
HTTP_SEC_CH_UA_PLATFORM = getattr(settings, "DJANGO_ACTIVITY_LOG_PLATFORM", "HTTP_SEC_CH_UA_PLATFORM")
GNOME_SHELL_SESSION_MODE = getattr(settings, "DJANGO_ACTIVITY_LOG_OPERATING_SYSTEM", "GNOME_SHELL_SESSION_MODE")

USER_DB_CONSTRAINT = bool(getattr(settings, "DJANGO_ACTIVITY_LOG_USER_DB_CONSTRAINT", True))

# logging backend settings
LOGGING_BACKEND = getattr(
    settings, "DJANGO_ACTIVITY_LOG_LOGGING_BACKEND", "activitylog.backends.ModelBackend"
)

# Models which Django Activity Log will not log.
# By default, all but some models will be audited.
# The list of excluded models can be overwritten or extended
# by defining the following settings in the project.
UNREGISTERED_CLASSES = [
    CRUDEvent,
    LoginEvent,
    RequestEvent,
    CorsEvent,
    Migration,
    Session,
    Permission,
    ContentType,
    MigrationRecorder.Migration,
]

# Import and unregister LogEntry class only if Django Admin app is installed
if apps.is_installed("django.contrib.admin"):
    from django.contrib.admin.models import LogEntry

    UNREGISTERED_CLASSES += [LogEntry]

UNREGISTERED_CLASSES = getattr(
    settings, "DJANGO_ACTIVITY_LOG_UNREGISTERED_CLASSES_DEFAULT", UNREGISTERED_CLASSES
)
UNREGISTERED_CLASSES.extend(
    getattr(settings, "DJANGO_ACTIVITY_LOG_UNREGISTERED_CLASSES_EXTRA", [])
)
get_model_list(UNREGISTERED_CLASSES)

# Models which Django Activity Log WILL log.
# If the following setting is defined in the project,
# only the listed models will be audited, and every other
# model will be excluded.
REGISTERED_CLASSES = getattr(settings, "DJANGO_ACTIVITY_LOG_REGISTERED_CLASSES", [])
get_model_list(REGISTERED_CLASSES)

# URLs which Django Activity Log will not log.
# By default, all but some URL requests will be logged.
# The list of excluded URLs can be overwritten or extended
# by defining the following settings in the project.
# Note: it is a list of regular expressions.
UNREGISTERED_URLS = [r"^/admin/", r"^/static/", r"^/favicon.ico$"]
UNREGISTERED_URLS = getattr(
    settings, "DJANGO_ACTIVITY_LOG_UNREGISTERED_URLS_DEFAULT", UNREGISTERED_URLS
)
UNREGISTERED_URLS.extend(getattr(settings, "DJANGO_ACTIVITY_LOG_UNREGISTERED_URLS_EXTRA", []))

# URLs which Django Activity Log WILL log.
# If the following setting is defined in the project,
# only the listed URLs will be audited, and every other
# URL will be excluded.
REGISTERED_URLS = getattr(settings, "DJANGO_ACTIVITY_LOG_REGISTERED_URLS", [])

# By default all modules are listed in the admin.
# This can be changed with the following settings.
ADMIN_SHOW_MODEL_EVENTS = getattr(
    settings, "DJANGO_ACTIVITY_LOG_ADMIN_SHOW_MODEL_EVENTS", True
)
ADMIN_SHOW_AUTH_EVENTS = getattr(settings, "DJANGO_ACTIVITY_LOG_ADMIN_SHOW_AUTH_EVENTS", True)

ADMIN_SHOW_REQUEST_EVENTS = getattr(
    settings, "DJANGO_ACTIVITY_LOG_ADMIN_SHOW_REQUEST_EVENTS", True
)

ADMIN_SHOW_CORS_EVENTS = getattr(
    settings, "DJANGO_ACTIVITY_LOG_ADMIN_SHOW_CORS_EVENTS", True
)

# project defined callbacks
CRUD_DIFFERENCE_CALLBACKS = []
CRUD_DIFFERENCE_CALLBACKS = getattr(
    settings, "DJANGO_ACTIVITY_LOG_CRUD_DIFFERENCE_CALLBACKS", CRUD_DIFFERENCE_CALLBACKS
)
DATABASE_ALIAS = getattr(
    settings, "DJANGO_ACTIVITY_LOG_DATABASE_ALIAS", django.db.utils.DEFAULT_DB_ALIAS
)
# The callbacks could come in as an iterable of strings, where each string is the
# package.module.function
for idx, callback in enumerate(CRUD_DIFFERENCE_CALLBACKS):
    if not callable(callback):  # keep as is if it is callable
        CRUD_DIFFERENCE_CALLBACKS[idx] = getattr(
            import_module(".".join(callback.split(".")[:-1])),
            callback.split(".")[-1],
            None,
        )

"""although this setting "exists" here we do not intend to use it anywhere due to test run
issues maybe we can properly solve this at a latter time. instead, anything inside of this
library should do the same getattr check here, based on normal `settings` from
`django.conf`."""
CRUD_EVENT_NO_CHANGED_FIELDS_SKIP = getattr(
    settings, "DJANGO_ACTIVITY_LOG_CRUD_EVENT_NO_CHANGED_FIELDS_SKIP", False
)

"""Purge table optimization:
If TRUNCATE_TABLE_SQL_STATEMENT is not empty, we use it as custom sql statement to speed up
table truncation bypassing ORM, i.e.:

  DJANGO_ACTIVITY_LOG_TRUNCATE_TABLE_SQL_STATEMENT = 'TRUNCATE TABLE "{db_table}"'

Else we use Django Orm as follows:

  model.objects.all().delete()

which is however much costly when many rows are involved"""
TRUNCATE_TABLE_SQL_STATEMENT = getattr(
    settings, "DJANGO_ACTIVITY_LOG_TRUNCATE_TABLE_SQL_STATEMENT", ""
)

# Changeview filters configuration
CRUD_EVENT_LIST_FILTER = getattr(
    settings,
    "DJANGO_ACTIVITY_LOG_CRUD_EVENT_LIST_FILTER",
    [
        "event_type",
        "content_type",
        "user",
        "datetime",
    ],
)
LOGIN_EVENT_LIST_FILTER = getattr(
    settings,
    "DJANGO_ACTIVITY_LOG_LOGIN_EVENT_LIST_FILTER",
    [
        "login_type",
        "user",
        "datetime",
    ],
)
REQUEST_EVENT_LIST_FILTER = getattr(
    settings,
    "DJANGO_ACTIVITY_LOG_REQUEST_EVENT_LIST_FILTER",
    [
        "method",
        "user",
        "datetime",
    ],
)

CORS_EVENT_LIST_FILTER = getattr(
    settings,
    "DJANGO_ACTIVITY_LOG_CORS_EVENT_LIST_FILTER",
    [
        "method",
        "user",
        "datetime",
    ],
)

# Search fields configuration
CRUD_EVENT_SEARCH_FIELDS = getattr(
    settings,
    "DJANGO_ACTIVITY_LOG_CRUD_EVENT_SEARCH_FIELDS",
    [
        "=object_id",
        "object_json_repr",
    ],
)
LOGIN_EVENT_SEARCH_FIELDS = getattr(
    settings,
    "DJANGO_ACTIVITY_LOG_LOGIN_EVENT_SEARCH_FIELDS",
    [
        "=remote_ip",
        "username",
    ],
)

REQUEST_EVENT_SEARCH_FIELDS = getattr(
    settings,
    "DJANGO_ACTIVITY_LOG_REQUEST_EVENT_SEARCH_FIELDS",
    [
        "=remote_ip",
        "user__username",
        "url",
        "query_string",
    ],
)

CORS_EVENT_SEARCH_FIELDS = getattr(
    settings,
    "DJANGO_ACTIVITY_LOG_CORS_EVENT_SEARCH_FIELDS",
    [
        "=remote_ip",
        "user__username",
        "url",
        "query_string",
    ],
)

READONLY_EVENTS = getattr(settings, "DJANGO_ACTIVITY_LOG_READONLY_EVENTS", False)

GEOIP_PATH = os.path.join('local/GeoLite2-City.mmdb')
