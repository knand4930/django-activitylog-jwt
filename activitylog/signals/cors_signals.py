import re
from importlib import import_module
from django.conf import settings
from django.contrib.auth import SESSION_KEY as AUTH_SESSION_KEY
from django.contrib.auth import get_user_model
from django.contrib.gis.geoip2 import GeoIP2
from django.contrib.sessions.models import Session
from django.core.signals import request_started
from django.http.cookie import SimpleCookie
from django.utils import timezone
from django.utils.module_loading import import_string
from rest_framework_jwt.utils import jwt_decode_handler

from activitylog.settings import (
    LOGGING_BACKEND,
    REGISTERED_URLS,
    REMOTE_ADDR_HEADER,
    UNREGISTERED_URLS,
    WATCH_CORS_EVENTS, HTTP_SEC_CH_UA, HTTP_SEC_CH_UA_PLATFORM, GNOME_SHELL_SESSION_MODE,
)

session_engine = import_module(settings.SESSION_ENGINE)
audit_logger = import_string(LOGGING_BACKEND)()


def should_log_url(url):
    # check if current url is blacklisted
    for unregistered_url in UNREGISTERED_URLS:
        pattern = re.compile(unregistered_url)
        if pattern.match(url):
            return False

    # only audit URLs listed in REGISTERED_URLS (if it's set)
    if len(REGISTERED_URLS) > 0:
        for registered_url in REGISTERED_URLS:
            pattern = re.compile(registered_url)
            if pattern.match(url):
                return True
        return False

    # all good
    return True


def cors_started_handler(sender, **kwargs):
    global authorization
    environ = kwargs.get("environ")
    scope = kwargs.get("scope")
    frontend_url = None
    browser = None
    platform = None
    operating_system = None

    if environ:
        path = environ["PATH_INFO"]
        cookie_string = environ.get("HTTP_COOKIE")
        authorization = environ.get('HTTP_AUTHORIZATION')
        query_string = environ["QUERY_STRING"]
        frontend_url = environ.get("HTTP_X_FRONTEND_URL")
        url_method = environ.get("HTTP_URL_METHOD")
        remote_ip = environ.get(REMOTE_ADDR_HEADER, None)
        browser = environ.get(HTTP_SEC_CH_UA, None)
        platform = environ.get(HTTP_SEC_CH_UA_PLATFORM, None)
        operating_system = environ.get(GNOME_SHELL_SESSION_MODE, None)

    else:
        path = scope.get("path")
        frontend_url = scope.get("HTTP_X_FRONTEND_URL")
        url_method = scope.get("HTTP_URL_METHOD")
        headers = dict(scope.get("headers"))
        cookie_string = headers.get(b"cookie")
        if isinstance(cookie_string, bytes):
            cookie_string = cookie_string.decode("utf-8")
        remote_ip = next(iter(scope.get("client", ("0.0.0.0", 0))))
        query_string = scope.get("query_string")

    if not frontend_url:
        return

    if not should_log_url(path):
        return
    if not should_log_url(frontend_url):
        return

    user = None
    # get the user from cookies
    if not user and cookie_string:
        cookie = SimpleCookie()
        cookie.load(cookie_string)
        session_cookie_name = settings.SESSION_COOKIE_NAME
        if session_cookie_name in cookie:
            session_id = cookie[session_cookie_name].value

            try:
                session = session_engine.SessionStore(session_key=session_id).load()
            except Session.DoesNotExist:
                session = None

            if session and AUTH_SESSION_KEY in session:
                user_id = session.get(AUTH_SESSION_KEY)
                try:
                    user = get_user_model().objects.get(id=user_id)
                except Exception:
                    user = None

    elif not user and authorization:
        try:
            jwt_token = authorization.split()[1]
        except Exception:
            jwt_token = authorization.split()[0]

        payload = jwt_decode_handler(jwt_token)
        user_id = payload["user_id"]
        try:
            user = get_user_model().objects.get(id=user_id)
        except Exception:
            user = None

    try:
        g = GeoIP2()
        lat, long = g.lat_lon(remote_ip)
        city = g.city(remote_ip)
        country = g.country(remote_ip)
    except Exception:
        lat = None
        long = None
        city = None
        country = None

    audit_logger.cors(
        {
            "url": frontend_url,
            "method": url_method,
            "query_string": query_string,
            "user_id": getattr(user, "id", None),
            "browser": browser,
            "platform": platform,
            "operating_system": operating_system,
            "remote_ip": remote_ip,
            "latitude": lat,
            "longitude": long,
            "city": city,
            "country": country,
            "datetime": timezone.now(),
        }
    )


if WATCH_CORS_EVENTS:
    request_started.connect(
        cors_started_handler, dispatch_uid="activity_log_signals_cors_started"
    )
