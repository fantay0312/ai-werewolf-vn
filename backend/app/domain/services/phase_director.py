from __future__ import annotations

from dataclasses import dataclass

from app.domain.commands.player_commands import PlayerCommand
from app.domain.kernel.snapshot import GameSnapshot
from app.domain.services.command_validator import CommandValidator, PHASE_ACTIONS
from app.models.game_state import ActionType, GamePhase


class PhaseValidationError(ValueError):
    """Raised when a command violates the current phase contract."""


@dataclass
class PhaseDirector:
    validator: CommandValidator = CommandValidator()

    def validate(self, snapshot: GameSnapshot, command: PlayerCommand) -> None:
        issues = self.validator.validate(snapshot, command)
        if issues:
            raise PhaseValidationError("；".join(issues))

    def build_action_window(self, snapshot: GameSnapshot, actor_id: int) -> list[dict[str, object]]:
        allowed_actions = sorted(
            PHASE_ACTIONS.get(snapshot.phase, set()),
            key=lambda action: action.value,
        )
        return [
            {
                "type": action.value,
                "requires_target": action
                in {ActionType.VOTE, ActionType.KILL, ActionType.CHECK, ActionType.GUARD, ActionType.SHOOT, ActionType.POISON, ActionType.SAVE},
                "phase": snapshot.phase.value,
                "actor_id": actor_id,
            }
            for action in allowed_actions
        ]

    def phase_contract(self, snapshot: GameSnapshot, actor_id: int) -> dict[str, object]:
        return {
            "phase": snapshot.phase.value,
            "day": snapshot.day,
            "current_speaker_id": snapshot.current_speaker_id,
            "allowed_actions": self.build_action_window(snapshot, actor_id),
            "alive_player_ids": list(snapshot.alive_player_ids),
            "dead_player_ids": list(snapshot.dead_player_ids),
            "sheriff_id": snapshot.sheriff_id,
        }
