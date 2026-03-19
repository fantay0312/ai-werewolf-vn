from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, MutableMapping, Optional

from app.models.game_state import GamePhase, GameState, Player


@dataclass(frozen=True)
class MemoryPhaseTransition:
    actor_id: int
    previous_day: Optional[int]
    previous_phase: Optional[GamePhase]
    current_day: int
    current_phase: GamePhase
    day_changed: bool
    phase_changed: bool


@dataclass(frozen=True)
class MemoryRolloverPlan:
    transition: MemoryPhaseTransition
    should_roll_recent_dialogue: bool
    should_reset_focus: bool
    metadata_updates: Dict[str, Any] = field(default_factory=dict)
    notes: tuple[str, ...] = ()


class MemoryLifecycleManager:
    META_KEY = "_runtime_meta"

    def build_plan_from_player(self, player: Player, game_state: GameState) -> MemoryRolloverPlan:
        memory_payload = player.ai_memory or {}
        meta = memory_payload.get(self.META_KEY, {})
        previous_day = meta.get("last_seen_day")
        previous_phase_raw = meta.get("last_seen_phase")
        previous_phase = None
        if previous_phase_raw is not None:
            try:
                previous_phase = GamePhase(previous_phase_raw)
            except ValueError:
                previous_phase = None

        transition = MemoryPhaseTransition(
            actor_id=player.id,
            previous_day=previous_day,
            previous_phase=previous_phase,
            current_day=game_state.day,
            current_phase=game_state.phase,
            day_changed=previous_day is not None and previous_day != game_state.day,
            phase_changed=previous_phase is not None and previous_phase != game_state.phase,
        )

        notes = []
        if transition.phase_changed:
            notes.append(f"phase rollover {previous_phase_raw} -> {game_state.phase.value}")
        if transition.day_changed:
            notes.append(f"day rollover {previous_day} -> {game_state.day}")

        return MemoryRolloverPlan(
            transition=transition,
            should_roll_recent_dialogue=transition.phase_changed,
            should_reset_focus=transition.phase_changed,
            metadata_updates={
                "last_seen_day": game_state.day,
                "last_seen_phase": game_state.phase.value,
            },
            notes=tuple(notes),
        )

    def apply_legacy_rollover(
        self,
        memory_payload: Optional[Mapping[str, Any]],
        plan: MemoryRolloverPlan,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = dict(memory_payload or {})
        recent_layer = dict(payload.get("recent_layer") or {})

        if plan.should_roll_recent_dialogue:
            current_dialogue = list(recent_layer.get("current_phase_dialogue") or [])
            if current_dialogue:
                recent_layer["previous_phase_dialogue"] = current_dialogue
                recent_layer["current_phase_dialogue"] = []

        if plan.should_reset_focus:
            recent_layer["current_focus"] = {"topic": "", "key_players": []}

        payload["recent_layer"] = recent_layer
        meta = dict(payload.get(self.META_KEY) or {})
        meta.update(plan.metadata_updates)
        payload[self.META_KEY] = meta
        return payload

    def stamp_runtime_meta(
        self,
        memory_payload: Optional[MutableMapping[str, Any]],
        game_state: GameState,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = dict(memory_payload or {})
        meta = dict(payload.get(self.META_KEY) or {})
        meta.update(
            {
                "last_seen_day": game_state.day,
                "last_seen_phase": game_state.phase.value,
            }
        )
        payload[self.META_KEY] = meta
        return payload
