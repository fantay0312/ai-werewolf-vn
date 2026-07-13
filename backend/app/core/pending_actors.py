"""Pure pending-actor queries over GameState.

Shared by the game manager (to schedule AI turns) and the view projectors
(to expose `ai_pending` so clients can hold the phase countdown until every
AI has finished acting).
"""
from __future__ import annotations

from typing import List

from app.core.rules import Rules
from app.models.game_state import GamePhase, GameState, Player, Role

# Phase -> set of roles/conditions that should act
PHASE_ACTOR_RULES = {
    GamePhase.GAME_START: lambda p, g: True,
    GamePhase.NIGHT_WOLF_DISCUSS: lambda p, g: p.role in (Role.WOLF, Role.WOLF_KING),
    GamePhase.NIGHT_WOLF_VOTE: lambda p, g: p.role in (Role.WOLF, Role.WOLF_KING),
    GamePhase.NIGHT_SEER: lambda p, g: p.role == Role.SEER,
    GamePhase.NIGHT_WITCH: lambda p, g: p.role == Role.WITCH,
    GamePhase.NIGHT_GUARD: lambda p, g: p.role == Role.GUARD,
    GamePhase.DAY_DISCUSS: lambda p, g: True,
    GamePhase.DAY_VOTE: lambda p, g: True,
    GamePhase.DAY_PK_VOTE: lambda p, g: p.id not in g.pk_candidates,
    GamePhase.SHERIFF_ELECTION: lambda p, g: True,
    GamePhase.SHERIFF_SPEECH: lambda p, g: p.id in g.sheriff_candidate_ids,
    GamePhase.SHERIFF_VOTE: lambda p, g: True,
}

SPEECH_PHASES = {
    GamePhase.DAY_DISCUSS,
    GamePhase.DAY_LAST_WORDS,
    GamePhase.SHERIFF_SPEECH,
    GamePhase.DAY_PK_SPEECH,
}


def get_pending_ai_players(game: GameState) -> List[Player]:
    """Identify AI players that need to act in the current phase."""
    pending: List[Player] = []

    if game.phase in SPEECH_PHASES:
        current_speaker_id = None
        if game.speaking_order and game.current_speaker_index < len(game.speaking_order):
            current_speaker_id = game.speaking_order[game.current_speaker_index]
        if current_speaker_id is None:
            return pending
        player = next((p for p in game.players if p.id == current_speaker_id), None)
        if (
            player
            and not player.is_human
            and not player.has_acted
            and (
                player.is_alive
                or game.phase in {GamePhase.DAY_LAST_WORDS, GamePhase.DAY_PK_SPEECH}
            )
        ):
            return [player]
        return pending

    for p in game.players:
        if p.has_acted:
            continue

        # Special: hunter skill - dead hunter/wolf_king who can shoot
        if game.phase == GamePhase.HUNTER_SKILL:
            alive_wolves = len([
                wolf for wolf in game.players
                if wolf.is_alive and wolf.role in (Role.WOLF, Role.WOLF_KING)
            ])
            if (
                not p.is_human
                and not p.is_alive
                and p.role in (Role.HUNTER, Role.WOLF_KING)
                and not p.gun_used
                and Rules.can_shoot(p, p.death_cause, alive_wolves=alive_wolves)
            ):
                pending.append(p)
            continue

        # Special: sheriff transfer - dead sheriff must hand over or tear badge
        if game.phase == GamePhase.SHERIFF_TRANSFER:
            if not p.is_human and not p.is_alive and p.is_sheriff and not p.has_acted:
                pending.append(p)
            continue

        # Normal phases: only alive AI players
        if p.is_human or not p.is_alive:
            continue

        rule = PHASE_ACTOR_RULES.get(game.phase)
        if rule and rule(p, game):
            pending.append(p)

    return pending


def has_pending_ai(game: GameState) -> bool:
    """True while at least one AI still has to act in the current phase."""
    return len(get_pending_ai_players(game)) > 0
