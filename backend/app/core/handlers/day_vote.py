from app.core.handlers.vote_collection_base import VoteCollectionHandler
from app.models.game_state import GamePhase, Player


class DayVoteHandler(VoteCollectionHandler):
    votes_attribute = "votes"
    cast_event = "day_vote_cast"
    result_phase = GamePhase.DAY_VOTE_RESULT

    def get_phase(self) -> GamePhase:
        return GamePhase.DAY_VOTE

    def on_enter(self):
        eligible_voter_ids = [player.id for player in self.get_alive_players()]
        self.add_log(
            "请投票放逐一名玩家。",
            data=self.build_event_data(
                "day_vote_started",
                participant_ids=eligible_voter_ids,
                eligible_voter_ids=eligible_voter_ids,
                eligible_voter_count=len(eligible_voter_ids),
                eligible_target_ids=eligible_voter_ids,
                allow_abstain=True,
                sheriff_id=self.game.sheriff_id,
                sheriff_vote_weight=2 if self.game.sheriff_id else 1,
            ),
        )
        self.game.votes = {}
        self.reset_actions()

    def _eligible_voters(self) -> list[Player]:
        return self.get_alive_players()

    def _is_eligible_target(self, target_id: int) -> bool:
        return self.is_alive_target(target_id)

    def _cast_content(self, player: Player, target_id: int) -> str:
        return f"{player.id}号玩家完成投票。"
