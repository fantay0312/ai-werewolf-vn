from __future__ import annotations

from dataclasses import dataclass

from app.domain.commands.base import Command
from app.models.action_model import ActionRequest
from app.models.game_state import ActionType, GamePhase


@dataclass(frozen=True)
class PlayerCommand(Command):
    action_type: ActionType = ActionType.PASS
    target_id: int | None = None
    content: str | None = None

    @classmethod
    def from_action(
        cls,
        game_id: str,
        phase: GamePhase,
        action: ActionRequest,
        *,
        source: str = "human",
    ) -> "PlayerCommand":
        return cls(
            game_id=game_id,
            actor_id=action.player_id,
            phase=phase,
            source=source,
            action_type=action.type,
            target_id=action.target_id,
            content=action.content,
        )
