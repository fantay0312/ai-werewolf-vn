from __future__ import annotations

from app.models.api_models import GameLogView, GameStateView, PlayerView
from app.models.game_state import GameState
from app.application.projections.projection_policy import (
    can_view_log,
    visible_has_acted,
    visible_pk_votes,
    visible_portrait,
    visible_role,
    visible_skill_usage,
    visible_votes,
)


class PublicViewProjector:
    def project(self, game: GameState) -> GameStateView:
        return GameStateView(
            session_id=game.session_id,
            day=game.day,
            phase=game.phase,
            players=[
                PlayerView(
                    id=player.id,
                    name=player.name,
                    role=visible_role(game, player),
                    portrait=visible_portrait(game, player),
                    is_human=False,
                    is_alive=player.is_alive,
                    is_sheriff=player.is_sheriff,
                    has_acted=visible_has_acted(game, player),
                    poison_used=player.poison_used if visible_skill_usage(game, player) else False,
                    antidote_used=player.antidote_used if visible_skill_usage(game, player) else False,
                    gun_used=player.gun_used if visible_skill_usage(game, player) else False,
                )
                for player in game.players
            ],
            game_logs=[
                GameLogView(
                    id=log.id,
                    day=log.day,
                    phase=log.phase,
                    content=log.content,
                    player_id=log.player_id,
                    is_public=log.is_public,
                    type=log.type,
                    data=log.data,
                )
                for log in game.game_logs
                if can_view_log(game, log)
            ],
            time_remaining=game.time_remaining,
            winner=game.winner,
            votes=visible_votes(game),
            pk_votes=visible_pk_votes(game),
            pk_candidates=game.pk_candidates,
            wolf_kill_target=None,
            dead_players=game.dead_players,
            sheriff_candidate_ids=game.sheriff_candidate_ids,
            sheriff_id=game.sheriff_id,
            election_explode_count=game.election_explode_count,
            pending_sheriff_election=game.pending_sheriff_election,
            election_cancelled=game.election_cancelled,
            speaking_order=game.speaking_order,
            current_speaker_index=game.current_speaker_index,
            wolf_discuss_messages=[],
        )
