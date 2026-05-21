"""Database health monitoring with automatic failover marking."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from django.utils import timezone

logger = logging.getLogger(__name__)


class DatabaseHealthMonitor:
    """Check the health of configured database connections."""

    def check_all(self) -> Dict[str, Any]:
        from activitylog.models import DatabaseConfig
        results = {}
        for cfg in DatabaseConfig.objects.filter(is_active=True):
            results[str(cfg.id)] = self.check_single(cfg)
        return results

    def check_single(self, cfg, save: bool = True) -> Dict[str, Any]:
        """Run a health check for one DatabaseConfig.

        :param cfg: A DatabaseConfig instance.
        :param save: Whether to persist health status back to the DB.
        """
        from activitylog.models import DatabaseConfig

        result: Dict[str, Any] = {
            "id": str(cfg.id),
            "name": cfg.name,
            "engine": cfg.engine,
            "healthy": False,
            "error": None,
            "latency_ms": None,
            "checked_at": timezone.now().isoformat(),
        }

        engine = cfg.engine

        try:
            import time
            t0 = time.perf_counter()

            if engine in (DatabaseConfig.POSTGRESQL, DatabaseConfig.MYSQL, DatabaseConfig.SQLITE):
                self._check_django_db(cfg)
            elif engine == DatabaseConfig.CLICKHOUSE:
                self._check_clickhouse(cfg)
            elif engine == DatabaseConfig.MONGODB:
                self._check_mongo(cfg)
            elif engine == DatabaseConfig.SCYLLADB:
                self._check_scylla(cfg)
            else:
                self._check_django_db(cfg)

            elapsed_ms = (time.perf_counter() - t0) * 1000
            result["healthy"] = True
            result["latency_ms"] = round(elapsed_ms, 2)

        except Exception as exc:
            result["healthy"] = False
            result["error"] = str(exc)
            logger.warning("Health check failed for '%s': %s", cfg.name, exc)

        if save and cfg.pk:
            try:
                cfg.is_healthy = result["healthy"]
                cfg.health_error = result["error"]
                cfg.last_health_check = timezone.now()
                cfg.save(update_fields=["is_healthy", "health_error", "last_health_check"])
            except Exception:
                pass

        return result

    def _check_django_db(self, cfg) -> None:
        from activitylog.routing.registry import ensure_config_registered
        alias = ensure_config_registered(cfg)
        from django.db import connections
        conn = connections[alias]
        conn.ensure_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT 1")

    def _check_clickhouse(self, cfg) -> None:
        from django.conf import settings as django_settings
        ch_cfg = getattr(django_settings, "ACTIVITYLOG_CLICKHOUSE", {})
        try:
            from clickhouse_driver import Client
        except ImportError as exc:
            raise RuntimeError("clickhouse-driver not installed") from exc
        client = Client(
            host=cfg.host,
            port=cfg.port or ch_cfg.get("port", 9000),
            database=cfg.database_name,
            user=cfg.username or "default",
            password=cfg.password or "",
        )
        client.execute("SELECT 1")

    def _check_mongo(self, cfg) -> None:
        try:
            import pymongo
        except ImportError as exc:
            raise RuntimeError("pymongo not installed") from exc
        uri = f"mongodb://{cfg.host}:{cfg.port or 27017}"
        client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=3000)
        client.server_info()
        client.close()

    def _check_scylla(self, cfg) -> None:
        try:
            from cassandra.cluster import Cluster
        except ImportError as exc:
            raise RuntimeError("cassandra-driver not installed") from exc
        cluster = Cluster(
            contact_points=[cfg.host],
            port=cfg.port or 9042,
            connect_timeout=3,
        )
        session = cluster.connect()
        session.execute("SELECT release_version FROM system.local")
        cluster.shutdown()
