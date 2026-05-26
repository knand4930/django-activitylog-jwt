"""Role-based permissions for the activity log API."""

from __future__ import annotations

from rest_framework.permissions import BasePermission


class IsActivityLogAdmin(BasePermission):
    """Full read/write access: Django superusers or users with the
    ``activitylog.view_all_logs`` permission."""

    message = "You must be an activity log administrator."

    def has_permission(self, request, view) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        return request.user.has_perm("activitylog.view_all_logs")


class IsActivityLogViewer(BasePermission):
    """Read-only access for users with ``activitylog.view_logs``."""

    message = "You need the 'view_logs' permission to access activity logs."

    def has_permission(self, request, view) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        if request.user.has_perm("activitylog.view_all_logs"):
            return True
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return request.user.has_perm("activitylog.view_logs")
        return False


class IsOwnerOrAdmin(BasePermission):
    """Users may only view their own log entries unless they are admins."""

    def has_permission(self, request, view) -> bool:
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj) -> bool:
        if request.user.is_superuser or request.user.has_perm("activitylog.view_all_logs"):
            return True
        return getattr(obj, "user_id", None) == request.user.pk


class DatabaseConfigPermission(BasePermission):
    """Only superusers or users with the db-config permission may manage DB configs."""

    message = "Database configuration requires administrator access."

    def has_permission(self, request, view) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        return request.user.has_perm("activitylog.manage_database_config")
