from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
import uuid

from app.models.game_state import GamePhase


class VisibilityScope(str, Enum):
    PUBLIC = "public"
    PRIVATE = "private"
    WOLF_TEAM = "wolf_team"
    ADMIN = "admin"


@dataclass(frozen=True)
class DomainEvent:
    name: str
    game_id: str
    day: int
    phase: GamePhase
    payload: dict[str, Any]
    visibility: VisibilityScope = VisibilityScope.PUBLIC
    actor_id: int | None = None
    target_id: int | None = None
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    causation_id: str | None = None
    correlation_id: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
