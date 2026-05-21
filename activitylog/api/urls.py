"""URL configuration for the activity log API.

Include in your project's URL conf:

    path("api/activitylog/", include("activitylog.api.urls")),
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from activitylog.api.views import (
    ActivityDashboardView,
    ActivitySSEView,
    CorsEventViewSet,
    CRUDEventViewSet,
    DatabaseConfigViewSet,
    LoginEventViewSet,
    RequestEventViewSet,
    RetentionPolicyViewSet,
    SystemEventViewSet,
)

router = DefaultRouter()
router.register(r"crud-events", CRUDEventViewSet, basename="crudevent")
router.register(r"login-events", LoginEventViewSet, basename="loginevent")
router.register(r"request-events", RequestEventViewSet, basename="requestevent")
router.register(r"cors-events", CorsEventViewSet, basename="corsevent")
router.register(r"system-events", SystemEventViewSet, basename="systemevent")
router.register(r"database-configs", DatabaseConfigViewSet, basename="databaseconfig")
router.register(r"retention-policies", RetentionPolicyViewSet, basename="retentionpolicy")

urlpatterns = [
    path("", include(router.urls)),
    path("dashboard/", ActivityDashboardView.as_view(), name="activitylog-dashboard"),
    path("stream/", ActivitySSEView.as_view(), name="activitylog-sse"),
]
