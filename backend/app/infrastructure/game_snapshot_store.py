from __future__ import annotations

import json
import os
import re
import tempfile
import threading
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.domain.events.base import DomainEvent, VisibilityScope
from app.models.game_state import GameState

DEFAULT_SNAPSHOT_DIR = (
    Path(__file__).resolve().parents[3] / "data" / "game_snapshots"
)
SNAPSHOT_SUFFIX = ".json"


class GameSnapshotRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int = Field(default=1, ge=1)
    session_id: str
    player_token: str
    created_at: datetime
    updated_at: datetime
    last_activity_at: float = 0.0
    game_state: GameState
    domain_events: list["PersistedDomainEvent"] = Field(default_factory=list)

    @classmethod
    def from_game_state(
        cls,
        game_state: GameState,
        player_token: str,
        *,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        last_activity_at: float | None = None,
        domain_events: list[DomainEvent] | None = None,
        schema_version: int = 1,
    ) -> "GameSnapshotRecord":
        now = datetime.now(timezone.utc)
        return cls(
            schema_version=schema_version,
            session_id=game_state.session_id,
            player_token=player_token,
            created_at=created_at or now,
            updated_at=updated_at or now,
            last_activity_at=last_activity_at if last_activity_at is not None else now.timestamp(),
            game_state=game_state,
            domain_events=[
                PersistedDomainEvent.from_domain_event(event)
                for event in (domain_events or [])
            ],
        )

    def to_domain_events(self) -> list[DomainEvent]:
        return [event.to_domain_event() for event in self.domain_events]


class PersistedDomainEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    game_id: str
    day: int
    phase: str
    payload: dict[str, Any]
    visibility: str = VisibilityScope.PUBLIC.value
    actor_id: int | None = None
    target_id: int | None = None
    event_id: str
    causation_id: str | None = None
    correlation_id: str | None = None
    created_at: datetime

    @classmethod
    def from_domain_event(cls, event: DomainEvent) -> "PersistedDomainEvent":
        return cls(
            name=event.name,
            game_id=event.game_id,
            day=event.day,
            phase=event.phase.value,
            payload=_to_jsonable(event.payload),
            visibility=event.visibility.value,
            actor_id=event.actor_id,
            target_id=event.target_id,
            event_id=event.event_id,
            causation_id=event.causation_id,
            correlation_id=event.correlation_id,
            created_at=event.created_at,
        )

    def to_domain_event(self) -> DomainEvent:
        from app.models.game_state import GamePhase

        return DomainEvent(
            name=self.name,
            game_id=self.game_id,
            day=self.day,
            phase=GamePhase(self.phase),
            payload=self.payload,
            visibility=VisibilityScope(self.visibility),
            actor_id=self.actor_id,
            target_id=self.target_id,
            event_id=self.event_id,
            causation_id=self.causation_id,
            correlation_id=self.correlation_id,
            created_at=self.created_at,
        )


GameSnapshotRecord.model_rebuild()


class GameSnapshotStore:
    """JSON file-backed snapshot store for game state."""

    def __init__(self, base_dir: str | Path | None = None):
        raw_base_dir = base_dir or os.getenv("GAME_SNAPSHOT_DIR") or DEFAULT_SNAPSHOT_DIR
        self.base_dir = Path(raw_base_dir).expanduser()
        self._lock = threading.RLock()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save(
        self,
        game_state: GameState,
        player_token: str,
        *,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        last_activity_at: float | None = None,
        domain_events: list[DomainEvent] | None = None,
        schema_version: int = 1,
    ) -> GameSnapshotRecord:
        """Persist a snapshot atomically and return the stored record."""
        with self._lock:
            existing = self.load(game_state.session_id)
            record = GameSnapshotRecord.from_game_state(
                game_state,
                player_token,
                created_at=created_at or (existing.created_at if existing else None),
                updated_at=updated_at,
                last_activity_at=last_activity_at,
                domain_events=domain_events,
                schema_version=schema_version,
            )
            self.base_dir.mkdir(parents=True, exist_ok=True)
            self._atomic_write(self._snapshot_path(record.session_id), record)
            return record

    def load(self, session_id: str) -> GameSnapshotRecord | None:
        """Load a single snapshot. Returns None for missing or invalid files."""
        path = self._snapshot_path(session_id)
        if not path.exists():
            return None
        return self._load_path(path)

    def load_all(self) -> list[GameSnapshotRecord]:
        """Load all valid snapshots in deterministic file order."""
        snapshots: list[GameSnapshotRecord] = []
        for path in sorted(self.base_dir.glob(f"*{SNAPSHOT_SUFFIX}")):
            record = self._load_path(path)
            if record is not None:
                snapshots.append(record)
        return snapshots

    def delete(self, session_id: str) -> bool:
        """Delete a snapshot file. Returns True when a file was removed."""
        path = self._snapshot_path(session_id)
        with self._lock:
            try:
                path.unlink()
            except FileNotFoundError:
                return False
            return True

    def is_ready(self) -> bool:
        try:
            self.base_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            return False
        return os.access(self.base_dir, os.W_OK)

    def _snapshot_path(self, session_id: str) -> Path:
        return self.base_dir / f"{self._safe_session_id(session_id)}{SNAPSHOT_SUFFIX}"

    def _safe_session_id(self, session_id: str) -> str:
        safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", session_id.strip())
        return safe or "snapshot"

    def _atomic_write(self, path: Path, record: GameSnapshotRecord) -> None:
        payload = record.model_dump(mode="json")
        tmp_file = None
        tmp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.base_dir,
                prefix=f".{path.stem}-",
                suffix=".tmp",
                delete=False,
            ) as handle:
                tmp_file = handle
                tmp_path = Path(handle.name)
                json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_path, path)
        except Exception:
            if tmp_path is not None:
                try:
                    tmp_path.unlink()
                except FileNotFoundError:
                    pass
            raise

    def _load_path(self, path: Path) -> GameSnapshotRecord | None:
        try:
            with path.open("r", encoding="utf-8") as handle:
                raw = json.load(handle)
            return GameSnapshotRecord.model_validate(raw)
        except (OSError, json.JSONDecodeError, ValidationError, ValueError, TypeError):
            return None


__all__ = [
    "DEFAULT_SNAPSHOT_DIR",
    "GameSnapshotRecord",
    "GameSnapshotStore",
    "PersistedDomainEvent",
]


def _to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return _to_jsonable(asdict(value))
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_jsonable(item) for item in value]
    return value
