from app.core.handlers.vote_result_base import VoteResultHandler
from app.models.game_state import GamePhase


class DayVoteResultHandler(VoteResultHandler):
    votes_attribute = "votes"
    tally_event = "day_vote_tallied"
    result_event_prefix = "day_vote"

    def get_phase(self) -> GamePhase:
        return GamePhase.DAY_VOTE_RESULT

    def _resolve_tie(self, max_votes, candidates, vote_counts, votes_snapshot) -> None:
        candidates_str = ", ".join(f"{player_id}号" for player_id in candidates)
        self.add_log(
            f"平票（{candidates_str}各{max_votes}票），进入PK环节。",
            data=self.build_event_data(
                "day_vote_tied",
                max_votes=max_votes,
                candidate_ids=list(candidates),
                tied_candidate_ids=list(candidates),
                pk_candidate_ids=list(candidates),
                pk_candidate_count=len(candidates),
                pk_round=1,
                vote_counts=self._sorted_vote_counts(vote_counts),
                votes=votes_snapshot,
                outcome="pk_required",
                dead_player_ids=list(self.game.dead_players),
                next_phase=GamePhase.DAY_PK_SPEECH.value,
            ),
        )
        self.game.pk_candidates = candidates
        self.game.pk_round = 1
        self.need_pk = True

    def _tie_outcome(self) -> str:
        return "tie"

    def _error_content(self, winner_id: int) -> str:
        return f"投票结果异常：未找到 {winner_id} 号玩家。"

    def _exile_content(self, winner_id: int, max_votes: int) -> str:
        return f"{winner_id}号玩家以{max_votes}票被放逐。"

    def _next_phase(self) -> GamePhase:
        if getattr(self, "need_pk", False):
            return GamePhase.DAY_PK_SPEECH
        return GamePhase.NIGHT_START
