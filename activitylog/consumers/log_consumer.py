"""Django Channels WebSocket consumer for real-time activity log streaming.

Add to your ASGI routing::

    from activitylog.consumers.log_consumer import ActivityLogConsumer

    websocket_urlpatterns = [
        path("ws/activitylog/", ActivityLogConsumer.as_asgi()),
    ]

Requires:
    channels>=4.0
    channels-redis (or another Channels layer)

Enable in settings::

    ACTIVITYLOG_REALTIME_ENABLED = True
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {"hosts": [("localhost", 6379)]},
        }
    }
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

try:
    from channels.generic.websocket import AsyncWebsocketConsumer as _Base

    class ActivityLogConsumer(_Base):
        """Broadcast new activity log events to connected WebSocket clients.

        Clients receive JSON messages of the form::

            {"type": "crud|login|request|cors|system", "event_id": "<uuid>"}
        """

        GROUP_NAME = "activitylog"

        async def connect(self) -> None:
            user = self.scope.get("user")
            if user is None or not user.is_authenticated:
                await self.close(code=4001)
                return

            if not (user.is_superuser or
                    user.has_perm("activitylog.view_logs") or
                    user.has_perm("activitylog.view_all_logs")):
                await self.close(code=4003)
                return

            await self.channel_layer.group_add(self.GROUP_NAME, self.channel_name)
            await self.accept()
            await self.send(text_data=json.dumps({"status": "connected"}))
            logger.debug("ActivityLogConsumer: %s connected", self.channel_name)

        async def disconnect(self, code: int) -> None:  # matches base signature
            await self.channel_layer.group_discard(self.GROUP_NAME, self.channel_name)
            logger.debug("ActivityLogConsumer: %s disconnected (%s)", self.channel_name, code)

        async def receive(
            self,
            text_data: str | None = None,
            bytes_data: bytes | None = None,  # noqa: ARG002
        ) -> None:
            try:
                payload = json.loads(text_data or "{}")
                await self.send(text_data=json.dumps({"ack": payload}))
            except Exception:
                pass

        async def log_event(self, event: dict[str, Any]) -> None:
            """Receive a channel-layer group broadcast and relay to WebSocket."""
            await self.send(text_data=json.dumps({
                "type": event.get("event_type"),
                "event_id": event.get("event_id"),
            }))

except ImportError:
    class ActivityLogConsumer:  # type: ignore[no-redef]
        """Stub — Django Channels is not installed."""

        @classmethod
        def as_asgi(cls):  # type: ignore[override]
            raise RuntimeError(
                "Django Channels is required for WebSocket support. "
                "Install it with: pip install channels channels-redis"
            )
