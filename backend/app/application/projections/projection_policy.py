from __future__ import annotations

from app.models.game_state import GameLog, GamePhase, GameState, Player, Role


def visible_role(game: GameState, player: Player, viewer: Player | None = None) -> Role | str:
    if game.phase == GamePhase.GAME_END:
        return player.role
    if viewer is not None and viewer.id == player.id:
        return player.role
    if (
        viewer is not None
        and viewer.role in (Role.WOLF, Role.WOLF_KING)
        and player.role in (Role.WOLF, Role.WOLF_KING)
    ):
        return player.role
    return "unknown"


def visible_skill_usage(game: GameState, player: Player, viewer: Player | None = None) -> bool:
    return game.phase == GamePhase.GAME_END or bool(viewer and viewer.id == player.id)


def visible_votes(game: GameState) -> dict[int, int]:
    if game.phase == GamePhase.DAY_VOTE_RESULT:
        return game.votes
    return {}


def visible_pk_votes(game: GameState) -> dict[int, int]:
    if game.phase == GamePhase.DAY_PK_RESULT:
        return game.pk_votes
    return {}


def can_view_log(game: GameState, log: GameLog, viewer: Player | None = None) -> bool:
    event_name = log.data.get("event") if log.data else None
    if game.phase == GamePhase.DAY_VOTE and event_name == "day_vote_cast":
        return viewer is not None and log.player_id == viewer.id
    return log.is_public or bool(viewer and log.player_id == viewer.id)
