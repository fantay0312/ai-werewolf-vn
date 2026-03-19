from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class ReplayEventRecord:
    index: int
    event_id: str
    event_name: str
    day: int
    phase: str
    payload: dict[str, Any] = field(default_factory=dict)
    created_at: datetime | None = None


@dataclass
class ReplayFrame:
    index: int
    event_name: str
    day: int
    phase: str
    summary: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class ReplayTimeline:
    game_id: str
    frames: list[ReplayFrame] = field(default_factory=list)


@dataclass
class EvalReport:
    game_id: str
    total_events: int
    ai_decisions: int
    fallback_decisions: int
    illegal_action_rate: float
    fallback_rate: float
