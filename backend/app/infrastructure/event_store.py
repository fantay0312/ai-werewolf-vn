from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Protocol

from app.domain.events.base import DomainEvent


class EventStore(Protocol):
    def append(self, event: DomainEvent) -> None: ...

    def list(self) -> list[DomainEvent]: ...

    def by_session(self, session_id: str) -> list[DomainEvent]: ...


@dataclass
class InMemoryEventStore:
    _events: dict[str, list[DomainEvent]] = field(default_factory=lambda: defaultdict(list))

    def append(self, event: DomainEvent) -> None:
        self._events[event.game_id].append(event)

    def append_many(self, events: list[DomainEvent]) -> None:
        for event in events:
            self.append(event)

    def list(self) -> list[DomainEvent]:
        events: list[DomainEvent] = []
        for session_events in self._events.values():
            events.extend(session_events)
        return events

    def by_session(self, session_id: str) -> list[DomainEvent]:
        return list(self._events.get(session_id, ()))

    def list_events(self, game_id: str) -> list[DomainEvent]:
        return self.by_session(game_id)

    def latest(self, game_id: str) -> DomainEvent | None:
        events = self._events.get(game_id)
        if not events:
            return None
        return events[-1]

    def clear(self, game_id: str) -> None:
        self._events.pop(game_id, None)

    def clear_all(self) -> None:
        self._events.clear()


event_store = InMemoryEventStore()
