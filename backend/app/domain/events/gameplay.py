from __future__ import annotations

from app.domain.events.base import DomainEvent, VisibilityScope
from app.models.game_state import ActionType, GameLog, GamePhase, GameState, Role


def game_created(game: GameState) -> DomainEvent:
    return DomainEvent(
        name="game_created",
        game_id=game.session_id,
        day=game.day,
        phase=game.phase,
        payload={
            "player_count": len(game.players),
            "human_player_id": next((p.id for p in game.players if p.is_human), None),
        },
        visibility=VisibilityScope.ADMIN,
    )


def player_action_received(
    game: GameState,
    *,
    actor_id: int,
    action_type: ActionType,
    target_id: int | None,
    source: str,
) -> DomainEvent:
    covert_vote_phases = {
        GamePhase.DAY_VOTE,
        GamePhase.DAY_PK_VOTE,
        GamePhase.SHERIFF_VOTE,
    }
    is_covert = (
        game.phase.value.startswith("NIGHT_")
        or (action_type == ActionType.VOTE and game.phase in covert_vote_phases)
    )
    visibility = VisibilityScope.PRIVATE if is_covert else VisibilityScope.PUBLIC
    payload = {
        "action_type": action_type.value,
        "source": source,
    }
    if is_covert:
        payload["viewer_ids"] = [actor_id]

    return DomainEvent(
        name="player_action_received",
        game_id=game.session_id,
        day=game.day,
        phase=game.phase,
        actor_id=actor_id,
        target_id=target_id,
        visibility=visibility,
        payload=payload,
    )


def phase_entered(game: GameState, previous_phase: GamePhase) -> DomainEvent:
    return DomainEvent(
        name="phase_entered",
        game_id=game.session_id,
        day=game.day,
        phase=game.phase,
        payload={
            "previous_phase": previous_phase.value,
            "current_phase": game.phase.value,
        },
        visibility=VisibilityScope.PUBLIC,
    )


def ai_decision_recorded(
    game: GameState,
    *,
    actor_id: int,
    model: str,
    phase: GamePhase,
    action_type: str,
    fallback_used: bool,
    issues: list[str],
) -> DomainEvent:
    return DomainEvent(
        name="ai_decision_recorded",
        game_id=game.session_id,
        day=game.day,
        phase=phase,
        actor_id=actor_id,
        visibility=VisibilityScope.ADMIN,
        payload={
            "model": model,
            "action_type": action_type,
            "fallback_used": fallback_used,
            "issues": issues,
        },
    )


def game_log_recorded(game: GameState, log: GameLog) -> DomainEvent:
    visibility = VisibilityScope.PUBLIC if log.is_public else VisibilityScope.PRIVATE
    payload = {
        "log_id": log.id,
        "log_type": log.type,
        "content": log.content,
        "player_id": log.player_id,
        "data": log.data or {},
    }

    if not log.is_public:
        if log.phase in {GamePhase.NIGHT_WOLF_DISCUSS, GamePhase.NIGHT_WOLF_VOTE}:
            visibility = VisibilityScope.WOLF_TEAM
            payload["wolf_ids"] = [
                player.id
                for player in game.players
                if player.role in (Role.WOLF, Role.WOLF_KING) and player.is_alive
            ]
        elif log.player_id is not None:
            payload["viewer_ids"] = [log.player_id]
        else:
            # Private system/audit logs without a player recipient should stay admin-only.
            visibility = VisibilityScope.ADMIN

    return DomainEvent(
        name="game_log_recorded",
        game_id=game.session_id,
        day=log.day,
        phase=log.phase,
        actor_id=log.player_id,
        visibility=visibility,
        payload=payload,
    )
