"""平票PK结果阶段处理器"""

from app.core.handlers.vote_result_base import VoteResultHandler
from app.models.game_state import GamePhase


class DayPKResultHandler(VoteResultHandler):
    votes_attribute = "pk_votes"
    tally_event = "day_pk_vote_tallied"
    result_event_prefix = "day_pk_vote"
    log_prefix = "PK投票结果"

    def get_phase(self) -> GamePhase:
        return GamePhase.DAY_PK_RESULT

    def _vote_payload(self, votes_snapshot: dict[int, int]) -> dict:
        return {"votes": votes_snapshot, "pk_votes": votes_snapshot}

    def _round_payload(self) -> dict:
        return {
            "pk_candidate_ids": list(self.game.pk_candidates),
            "pk_candidate_count": len(self.game.pk_candidates),
            "pk_round": self.game.pk_round,
        }

    def _resolve_tie(self, max_votes, candidates, vote_counts, votes_snapshot) -> None:
        candidates_str = ", ".join(f"{player_id}号" for player_id in candidates)
        self.add_log(
            f"PK后仍然平票（{candidates_str}各{max_votes}票），无人出局。",
            data=self.build_event_data(
                "day_pk_vote_tied",
                max_votes=max_votes,
                candidate_ids=list(candidates),
                tied_candidate_ids=list(candidates),
                **self._round_payload(),
                vote_counts=self._sorted_vote_counts(vote_counts),
                **self._vote_payload(votes_snapshot),
                outcome="tie_no_elimination",
                dead_player_ids=list(self.game.dead_players),
                next_phase=GamePhase.NIGHT_START.value,
            ),
        )

    def _tie_outcome(self) -> str:
        return "tie_no_elimination"

    def _error_content(self, winner_id: int) -> str:
        return f"PK结果异常：未找到 {winner_id} 号玩家。"

    def _exile_content(self, winner_id: int, max_votes: int) -> str:
        return f"PK结果：{winner_id}号玩家以{max_votes}票被放逐。"

    def _cleanup(self) -> None:
        self.game.pk_candidates = []
        self.game.pk_votes = {}
        self.game.pk_round = 0
