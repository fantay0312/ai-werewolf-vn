"""平票PK投票阶段处理器"""

from app.core.handlers.vote_collection_base import VoteCollectionHandler
from app.models.game_state import GamePhase, Player


class DayPKVoteHandler(VoteCollectionHandler):
    votes_attribute = "pk_votes"
    cast_event = "day_pk_vote_cast"
    result_phase = GamePhase.DAY_PK_RESULT

    def get_phase(self) -> GamePhase:
        return GamePhase.DAY_PK_VOTE

    def on_enter(self):
        self.game.pk_votes = {}
        pk_candidates = self.game.pk_candidates
        eligible_voter_ids = sorted(player.id for player in self._eligible_voters())
        candidates_str = ", ".join(f"{player_id}号" for player_id in pk_candidates)
        self.add_log(
            f"PK投票开始。请在 {candidates_str} 中选择一人投票。PK候选人不参与投票。",
            log_type="broadcast",
            data=self.build_event_data(
                "day_pk_vote_started",
                participant_ids=eligible_voter_ids,
                eligible_voter_ids=eligible_voter_ids,
                eligible_voter_count=len(eligible_voter_ids),
                eligible_target_ids=list(pk_candidates),
                pk_candidate_ids=list(pk_candidates),
                pk_candidate_count=len(pk_candidates),
                allow_abstain=True,
                sheriff_id=self.game.sheriff_id,
                sheriff_vote_weight=2 if self.game.sheriff_id else 1,
                pk_round=self.game.pk_round,
            ),
        )
        for player in self.game.players:
            player.has_acted = player not in self._eligible_voters()

    def _eligible_voters(self) -> list[Player]:
        return [
            player for player in self.game.players
            if player.is_alive and player.id not in self.game.pk_candidates
        ]

    def _is_eligible_target(self, target_id: int) -> bool:
        return target_id in self.game.pk_candidates

    def _cast_content(self, player: Player, target_id: int) -> str:
        target_label = "弃票" if target_id == 0 else f"{target_id}号"
        return f"{player.id}号投票给 {target_label}"

    def _vote_payload(self, votes_snapshot: dict[int, int]) -> dict:
        return {
            "pk_candidate_ids": list(self.game.pk_candidates),
            "pk_round": self.game.pk_round,
            "votes": votes_snapshot,
            "pk_votes": votes_snapshot,
            "votes_snapshot": votes_snapshot,
        }
