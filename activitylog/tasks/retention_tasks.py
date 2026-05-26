"""Celery tasks for log retention and automatic cleanup."""

from __future__ import annotations

import logging
from datetime import timedelta

from django.utils import timezone

logger = logging.getLogger(__name__)

try:
    from celery import shared_task
except ImportError:
    def shared_task(fn=None, **_):  # type: ignore[misc]
        if fn is None:
            return shared_task
        fn.delay = fn
        fn.apply_async = lambda *a, **k: fn(*a, **k)
        return fn


_EVENT_MODEL_MAP = {
    "crud": "activitylog.CRUDEvent",
    "login": "activitylog.LoginEvent",
    "request": "activitylog.RequestEvent",
    "cors": "activitylog.CorsEvent",
    "system": "activitylog.SystemEvent",
    "all": None,
}


def _get_model(dotted: str):
    from django.apps import apps
    app_label, model_name = dotted.split(".")
    return apps.get_model(app_label, model_name)


@shared_task(name="activitylog.enforce_retention_policies")
def enforce_retention_policies() -> dict:
    """Apply all active RetentionPolicy records. Designed for Celery Beat."""
    from activitylog.models import RetentionPolicy

    results = {}
    policies = RetentionPolicy.objects.filter(is_active=True)

    for policy in policies:
        count = _apply_policy(policy)
        policy.last_run = timezone.now()
        policy.records_deleted += count
        policy.save(update_fields=["last_run", "records_deleted"])
        results[policy.name] = count
        logger.info("RetentionPolicy '%s': deleted %d records", policy.name, count)

    return results


def _apply_policy(policy) -> int:
    """Delete records older than policy.retain_days and return count deleted."""
    cutoff = timezone.now() - timedelta(days=policy.retain_days)
    event_type = policy.event_type

    all_models = {
        "crud": "activitylog.CRUDEvent",
        "login": "activitylog.LoginEvent",
        "request": "activitylog.RequestEvent",
        "cors": "activitylog.CorsEvent",
        "system": "activitylog.SystemEvent",
    }

    if event_type == "all":
        targets = list(all_models.values())
    else:
        dotted = all_models.get(event_type)
        targets = [dotted] if dotted else []

    total = 0
    for dotted in targets:
        try:
            model = _get_model(dotted)
            qs = model.objects.filter(datetime__lt=cutoff)
            if policy.tenant_id and hasattr(model, "user"):
                qs = qs.filter(user__profile__tenant_id=policy.tenant_id)
            deleted, _ = qs.delete()
            total += deleted
        except Exception as exc:
            logger.error("RetentionPolicy '%s' failed for %s: %s", policy.name, dotted, exc)

    return total


@shared_task(name="activitylog.cleanup_old_logs")
def cleanup_old_logs(event_type: str = "all", days: int = 90) -> int:
    """One-off cleanup: delete logs older than ``days`` days.

    Useful for ad-hoc management or as a fallback when no policies exist.
    """
    from activitylog.models import RetentionPolicy
    tmp = RetentionPolicy(name="_adhoc", event_type=event_type, retain_days=days)
    count = _apply_policy(tmp)
    logger.info("cleanup_old_logs(%s, %d days): deleted %d records", event_type, days, count)
    return count


@shared_task(name="activitylog.recompute_integrity_hashes")
def recompute_integrity_hashes() -> dict:
    """Batch-recompute missing integrity hashes (e.g. after upgrade)."""
    from activitylog.models import CorsEvent, CRUDEvent, LoginEvent, RequestEvent, SystemEvent

    results = {}
    for model in (CRUDEvent, LoginEvent, RequestEvent, CorsEvent, SystemEvent):
        count = 0
        for obj in model.objects.filter(integrity_hash__isnull=True).iterator(chunk_size=500):
            obj.integrity_hash = obj.compute_integrity_hash()
            obj.save(update_fields=["integrity_hash"])
            count += 1
        results[model.__name__] = count
        logger.info("recompute_integrity_hashes: %s → %d updated", model.__name__, count)

    return results
