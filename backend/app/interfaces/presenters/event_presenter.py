from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel

from app.domain.events.base import DomainEvent
from app.models.events import GameEvent


class EventPresenter:
    def present(
        self,
        event: GameEvent | DomainEvent,
        *,
        session_id: str | None = None,
        viewer_id: int | None = None,
    ) -> dict[str, object]:
        if isinstance(event, DomainEvent):
            return {
                "event_id": event.event_id,
                "event_type": event.name,
                "session_id": event.game_id,
                "viewer_id": viewer_id,
                "day": event.day,
                "phase": event.phase.value,
                "visibility": event.visibility.value,
                "actor_id": event.actor_id,
                "target_id": event.target_id,
                "data": self._normalize(event.payload),
                "timestamp": event.created_at.isoformat(),
                "schema": "domain",
            }

        resolved_session_id = session_id or self._extract_session_id(event)
        return {
            "event_id": None,
            "event_type": event.event_type,
            "session_id": resolved_session_id,
            "viewer_id": viewer_id,
            "visibility": "public" if self._is_public_legacy_event(event) else "private",
            "data": self._normalize(event.data),
            "timestamp": event.timestamp,
            "schema": "legacy",
        }

    def to_sse(
        self,
        event: GameEvent | DomainEvent,
        *,
        session_id: str | None = None,
        viewer_id: int | None = None,
    ) -> dict[str, str]:
        payload = self.present(event, session_id=session_id, viewer_id=viewer_id)
        event_id = payload.get("event_id")
        sse_event = {"data": json.dumps(payload, ensure_ascii=False)}
        if event_id is not None:
            sse_event["id"] = str(event_id)
        return sse_event

    def _extract_session_id(self, event: GameEvent) -> str | None:
        for key in ("session_id", "game_id"):
            value = event.data.get(key)
            if isinstance(value, str) and value:
                return value
        return None

    def _is_public_legacy_event(self, event: GameEvent) -> bool:
        return "viewer_id" not in event.data and "viewer_ids" not in event.data and "wolf_ids" not in event.data

    def _normalize(self, value: Any) -> Any:
        if isinstance(value, Enum):
            return value.value
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        if isinstance(value, BaseModel):
            return self._normalize(value.model_dump())
        if is_dataclass(value):
            return self._normalize(asdict(value))
        if isinstance(value, dict):
            return {str(key): self._normalize(item) for key, item in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [self._normalize(item) for item in value]
        return value
