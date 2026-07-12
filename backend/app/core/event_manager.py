import asyncio
import logging
from collections import defaultdict
from collections.abc import Callable
from typing import Any

from app.config import get_server_config
from app.domain.events.base import DomainEvent, VisibilityScope
from app.infrastructure.runtime_metrics import runtime_metrics
from app.models.events import GameEvent

logger = logging.getLogger(__name__)

SessionViewerKey = tuple[str, int]
EventEnvelope = GameEvent | DomainEvent
MAX_SSE_QUEUES_PER_VIEWER = 2


class SSEQueueClosed:
    """Sentinel instructing an evicted SSE generator to terminate."""


SSE_QUEUE_CLOSED = SSEQueueClosed()
QueueEnvelope = EventEnvelope | SSEQueueClosed


class EventManager:
    """管理内部订阅和按局、按视角隔离的 SSE 队列。"""

    def __init__(self, queue_capacity: int | None = None):
        self._subscribers: dict[str, list[Callable[..., Any]]] = {}
        self._sse_queues: dict[SessionViewerKey, list[asyncio.Queue[QueueEnvelope]]] = defaultdict(list)
        self._queue_capacity = queue_capacity
        self._dropped_events = 0

    def reset(self) -> None:
        """测试辅助：清空所有订阅和 SSE 队列。"""
        self._subscribers.clear()
        self._sse_queues.clear()
        self._dropped_events = 0

    def subscribe(self, event_type: str, callback: Callable[..., Any]) -> None:
        """订阅事件。"""
        self._subscribers.setdefault(event_type, []).append(callback)

    async def publish(
        self,
        event: EventEnvelope,
        *,
        session_id: str | None = None,
        viewer_id: int | None = None,
        viewer_ids: list[int] | None = None,
        exclude_viewers: list[int] | None = None,
    ) -> None:
        """发布事件到内部订阅器和 SSE 连接。"""
        await self._notify_subscribers(event)

        resolved_session_id = self._resolve_session_id(event, session_id)
        if resolved_session_id is None:
            logger.warning("Skipping SSE delivery for %s because session_id is missing", self._event_name(event))
            return

        resolved_viewer_ids = self._resolve_viewer_targets(event, viewer_id, viewer_ids)
        target_queues = self._collect_target_queues(
            resolved_session_id,
            viewer_ids=resolved_viewer_ids,
            exclude_viewers=exclude_viewers,
        )

        for queue in target_queues:
            self._put_with_backpressure(queue, event, resolved_session_id)

    async def push_to_player(
        self,
        player_id: int,
        event: EventEnvelope,
        *,
        session_id: str | None = None,
    ) -> None:
        """向单个视角队列推送事件。"""
        await self.publish(event, session_id=session_id, viewer_id=player_id)

    async def broadcast(
        self,
        event: EventEnvelope,
        *,
        session_id: str | None = None,
        exclude_players: list[int] | None = None,
    ) -> None:
        """向某局内所有 SSE 视角广播事件。"""
        await self.publish(event, session_id=session_id, exclude_viewers=exclude_players)

    async def create_sse_queue(self, session_id: str, viewer_id: int = 0) -> asyncio.Queue[QueueEnvelope]:
        """为某局、某视角创建独立 SSE 队列。"""
        configured_capacity = (
            self._queue_capacity
            if self._queue_capacity is not None
            else get_server_config().sse_queue_capacity
        )
        queue: asyncio.Queue[QueueEnvelope] = asyncio.Queue(maxsize=max(1, configured_capacity))
        key = (session_id, viewer_id)
        queues = self._sse_queues[key]
        if len(queues) >= MAX_SSE_QUEUES_PER_VIEWER:
            evicted = queues.pop(0)
            self._close_queue(evicted)
            runtime_metrics.record_business_counter(
                "sse_queues_evicted_total",
                labels={"reason": "viewer_cap"},
                help_text="Total SSE queues evicted by per-viewer connection cap",
            )
            logger.warning(
                "Evicted oldest SSE queue for session %s viewer %s",
                session_id,
                viewer_id,
            )
        queues.append(queue)
        return queue

    def _put_with_backpressure(
        self,
        queue: asyncio.Queue[QueueEnvelope],
        event: EventEnvelope,
        session_id: str,
    ) -> None:
        if queue.full():
            queue.get_nowait()
            self._dropped_events += 1
            runtime_metrics.record_business_counter(
                "sse_events_dropped_total",
                labels={"reason": "queue_full"},
                help_text="Total SSE events dropped by backpressure policy",
            )
            logger.warning(
                "Dropped oldest SSE event for session %s; total_dropped=%s",
                session_id,
                self._dropped_events,
            )
        queue.put_nowait(event)

    def remove_sse_queue(
        self,
        session_id: str,
        viewer_id: int,
        queue: asyncio.Queue[QueueEnvelope] | None = None,
    ) -> None:
        """移除 SSE 队列。"""
        key = (session_id, viewer_id)
        queues = self._sse_queues.get(key)
        if not queues:
            return

        if queue is None:
            self._sse_queues.pop(key, None)
            return

        if queue in queues:
            queues.remove(queue)
        if not queues:
            self._sse_queues.pop(key, None)

    def _close_queue(self, queue: asyncio.Queue[QueueEnvelope]) -> None:
        if queue.full():
            queue.get_nowait()
        queue.put_nowait(SSE_QUEUE_CLOSED)

    async def _notify_subscribers(self, event: EventEnvelope) -> None:
        event_name = self._event_name(event)
        for callback in self._subscribers.get(event_name, []):
            try:
                result = callback(event)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.error("Error in subscriber for %s: %s", event_name, exc)

    def _event_name(self, event: EventEnvelope) -> str:
        if isinstance(event, DomainEvent):
            return event.name
        return event.event_type

    def _resolve_session_id(self, event: EventEnvelope, session_id: str | None) -> str | None:
        if session_id:
            return session_id

        if isinstance(event, DomainEvent):
            return event.game_id

        for key in ("session_id", "game_id"):
            value = event.data.get(key)
            if isinstance(value, str) and value:
                return value

        active_sessions = {active_session for active_session, _ in self._sse_queues}
        if len(active_sessions) == 1:
            return next(iter(active_sessions))

        return None

    def _resolve_viewer_targets(
        self,
        event: EventEnvelope,
        viewer_id: int | None,
        viewer_ids: list[int] | None,
    ) -> list[int] | None:
        if viewer_id is not None:
            return [viewer_id]
        if viewer_ids is not None:
            return list(dict.fromkeys(viewer_ids))

        if isinstance(event, DomainEvent):
            return self._resolve_domain_viewers(event)
        return self._resolve_legacy_viewers(event)

    def _resolve_domain_viewers(self, event: DomainEvent) -> list[int] | None:
        payload_viewers = event.payload.get("viewer_ids")
        if isinstance(payload_viewers, list):
            return [viewer for viewer in payload_viewers if isinstance(viewer, int)]

        payload_viewer = event.payload.get("viewer_id")
        if isinstance(payload_viewer, int):
            return [payload_viewer]

        if event.visibility == VisibilityScope.PUBLIC:
            return None

        if event.visibility == VisibilityScope.PRIVATE:
            return [event.actor_id] if event.actor_id is not None else []

        if event.visibility == VisibilityScope.WOLF_TEAM:
            wolf_ids = event.payload.get("wolf_ids")
            if isinstance(wolf_ids, list):
                return [viewer for viewer in wolf_ids if isinstance(viewer, int)]
            return []

        return []

    def _resolve_legacy_viewers(self, event: GameEvent) -> list[int] | None:
        data = event.data

        explicit_viewers = data.get("viewer_ids")
        if isinstance(explicit_viewers, list):
            return [viewer for viewer in explicit_viewers if isinstance(viewer, int)]

        explicit_viewer = data.get("viewer_id")
        if isinstance(explicit_viewer, int):
            return [explicit_viewer]

        if event.event_type == "wolf_message":
            wolf_ids = data.get("wolf_ids")
            if isinstance(wolf_ids, list):
                return [viewer for viewer in wolf_ids if isinstance(viewer, int)]
            return []

        return None

    def _collect_target_queues(
        self,
        session_id: str,
        *,
        viewer_ids: list[int] | None,
        exclude_viewers: list[int] | None,
    ) -> list[asyncio.Queue[QueueEnvelope]]:
        excluded = set(exclude_viewers or [])
        queues: set[asyncio.Queue[QueueEnvelope]] = set()

        if viewer_ids is None:
            for (active_session, active_viewer), active_queues in self._sse_queues.items():
                if active_session != session_id or active_viewer in excluded:
                    continue
                queues.update(active_queues)
            return list(queues)

        for target_viewer in viewer_ids:
            if target_viewer in excluded:
                continue
            queues.update(self._sse_queues.get((session_id, target_viewer), []))
        return list(queues)


event_manager = EventManager()
