from __future__ import annotations

from dataclasses import dataclass

from app.models.game_state import GamePhase, GameState


@dataclass(frozen=True)
class GameSnapshot:
    """Immutable view of the current game state for validators and schedulers."""

    game_id: str
    day: int
    phase: GamePhase
    alive_player_ids: tuple[int, ...]
    dead_player_ids: tuple[int, ...]
    sheriff_id: int | None
    current_speaker_id: int | None
    wolf_revote_resolver_id: int | None

    @classmethod
    def from_game_state(cls, game: GameState) -> "GameSnapshot":
        current_speaker_id = None
        if (
            game.speaking_order
            and 0 <= game.current_speaker_index < len(game.speaking_order)
        ):
            current_speaker_id = game.speaking_order[game.current_speaker_index]

        return cls(
            game_id=game.session_id,
            day=game.day,
            phase=game.phase,
            alive_player_ids=tuple(sorted(p.id for p in game.players if p.is_alive)),
            dead_player_ids=tuple(sorted(p.id for p in game.players if not p.is_alive)),
            sheriff_id=game.sheriff_id,
            current_speaker_id=current_speaker_id,
            wolf_revote_resolver_id=game.wolf_revote_resolver_id,
        )
