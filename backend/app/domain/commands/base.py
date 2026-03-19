from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.models.game_state import GamePhase


@dataclass(frozen=True)
class Command:
    game_id: str
    actor_id: int
    phase: GamePhase
    issued_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = "human"
