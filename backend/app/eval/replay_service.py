from __future__ import annotations

from app.domain.events.base import DomainEvent
from app.eval.models import ReplayFrame, ReplayTimeline


class ReplayService:
    def build_timeline(self, game_id: str, events: list[DomainEvent]) -> ReplayTimeline:
        timeline = ReplayTimeline(game_id=game_id)
        for index, event in enumerate(events):
            payload = dict(event.payload)
            payload.setdefault("visibility", event.visibility.value)
            timeline.frames.append(
                ReplayFrame(
                    index=index,
                    event_name=event.name,
                    day=event.day,
                    phase=event.phase.value,
                    summary=self._summarize(event),
                    payload=payload,
                )
            )
        return timeline

    def seek(self, timeline: ReplayTimeline, index: int) -> ReplayFrame | None:
        if 0 <= index < len(timeline.frames):
            return timeline.frames[index]
        return None

    def _summarize(self, event: DomainEvent) -> str:
        if event.name == "phase_entered":
            return f"进入阶段 {event.payload.get('current_phase')}"
        if event.name == "player_action_received":
            return f"{event.actor_id}号执行 {event.payload.get('action_type')}"
        if event.name == "game_log_recorded":
            data = event.payload.get("data", {})
            event_name = data.get("event")
            if event_name:
                return str(event_name)
            action_name = data.get("action")
            if action_name:
                return str(action_name)
            return str(event.payload.get("content", "game_log_recorded"))
        if event.name == "ai_decision_recorded":
            return f"AI {event.actor_id} 产生 {event.payload.get('action_type')}"
        return event.name
