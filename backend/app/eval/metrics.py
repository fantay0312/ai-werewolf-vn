from __future__ import annotations

from app.domain.events.base import DomainEvent
from app.eval.models import EvalReport


class EvalMetricsService:
    def build_report(self, game_id: str, events: list[DomainEvent]) -> EvalReport:
        ai_events = [event for event in events if event.name == "ai_decision_recorded"]
        fallback_count = sum(1 for event in ai_events if event.payload.get("fallback_used"))
        illegal_count = sum(1 for event in ai_events if event.payload.get("issues"))
        total_ai = len(ai_events)
        return EvalReport(
            game_id=game_id,
            total_events=len(events),
            ai_decisions=total_ai,
            fallback_decisions=fallback_count,
            illegal_action_rate=(illegal_count / total_ai) if total_ai else 0.0,
            fallback_rate=(fallback_count / total_ai) if total_ai else 0.0,
        )


MetricsService = EvalMetricsService
ReplayMetrics = EvalReport
