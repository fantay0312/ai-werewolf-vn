from __future__ import annotations

from app.models.api_models import GameLogView, GameStateView, PlayerView, WolfDiscussMessageView
from app.models.game_state import GamePhase, GameState, Player, Role
from app.application.projections.projection_policy import (
    can_view_log,
    visible_has_acted,
    visible_pk_votes,
    visible_portrait,
    visible_role,
    visible_skill_usage,
    visible_votes,
)


class PrivateViewProjector:
    def project(self, game: GameState, viewer: Player) -> GameStateView:
        return GameStateView(
            session_id=game.session_id,
            day=game.day,
            phase=game.phase,
            players=[self._player_view(game, player, viewer) for player in game.players],
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
                if can_view_log(game, log, viewer)
            ],
            time_remaining=game.time_remaining,
            winner=game.winner,
            votes=visible_votes(game, viewer),
            pk_votes=visible_pk_votes(game, viewer),
            pk_candidates=game.pk_candidates,
            wolf_kill_target=game.wolf_kill_target if viewer.role == Role.WITCH and game.phase == GamePhase.NIGHT_WITCH else None,
            dead_players=game.dead_players,
            sheriff_candidate_ids=game.sheriff_candidate_ids,
            sheriff_id=game.sheriff_id,
            election_explode_count=game.election_explode_count,
            pending_sheriff_election=game.pending_sheriff_election,
            election_cancelled=game.election_cancelled,
            speaking_order=game.speaking_order,
            current_speaker_index=game.current_speaker_index,
            wolf_discuss_messages=[
                WolfDiscussMessageView(
                    id=message.id,
                    speaker_id=message.speaker_id,
                    content=message.content,
                    round=message.round,
                )
                for message in game.wolf_discuss_messages
                if viewer.role in (Role.WOLF, Role.WOLF_KING)
            ],
        )

    def _player_view(self, game: GameState, player: Player, viewer: Player) -> PlayerView:
        role = visible_role(game, player, viewer)
        reveal_skill_usage = visible_skill_usage(game, player, viewer)

        return PlayerView(
            id=player.id,
            name=player.name,
            role=role,
            portrait=visible_portrait(game, player, viewer),
            is_human=viewer.id == player.id,
            is_alive=player.is_alive,
            is_sheriff=player.is_sheriff,
            has_acted=visible_has_acted(game, player, viewer),
            poison_used=player.poison_used if reveal_skill_usage else False,
            antidote_used=player.antidote_used if reveal_skill_usage else False,
            gun_used=player.gun_used if reveal_skill_usage else False,
        )
