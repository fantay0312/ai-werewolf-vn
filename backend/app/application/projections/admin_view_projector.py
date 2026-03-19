from __future__ import annotations

from app.models.api_models import GameLogView, GameStateView, PlayerView, WolfDiscussMessageView
from app.models.game_state import GameState


class AdminViewProjector:
    def project(self, game: GameState) -> GameStateView:
        return GameStateView(
            session_id=game.session_id,
            day=game.day,
            phase=game.phase,
            players=[
                PlayerView(
                    id=player.id,
                    name=player.name,
                    role=player.role,
                    portrait=player.portrait,
                    is_human=player.is_human,
                    is_alive=player.is_alive,
                    is_sheriff=player.is_sheriff,
                    has_acted=player.has_acted,
                    poison_used=player.poison_used,
                    antidote_used=player.antidote_used,
                    gun_used=player.gun_used,
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
            ],
            time_remaining=game.time_remaining,
            winner=game.winner,
            votes=game.votes,
            pk_votes=game.pk_votes,
            pk_candidates=game.pk_candidates,
            wolf_kill_target=game.wolf_kill_target,
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
            ],
        )
