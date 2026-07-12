"""平票PK结果阶段处理器"""
from typing import Optional
from app.core.phase_handler import PhaseHandler
from app.models.game_state import DeathCause, GamePhase
from app.models.action_model import ActionRequest


class DayPKResultHandler(PhaseHandler):
    def get_phase(self) -> GamePhase:
        return GamePhase.DAY_PK_RESULT

    def on_enter(self):
        pk_round = self.game.pk_round
        pk_candidates = list(self.game.pk_candidates)
        votes_snapshot = {int(k): v for k, v in self.game.pk_votes.items()}
        vote_counts = self.count_votes(votes_snapshot, sheriff_weighted=True)
        vote_entries = self._build_vote_entries(votes_snapshot)
        abstain_voter_ids = [entry["voter_id"] for entry in vote_entries if entry["target_id"] == 0]
        winner_id, max_votes, candidates = self.resolve_vote_winner(vote_counts)

        content = self.format_vote_log(votes_snapshot, prefix="PK投票结果")
        self.add_log(
            content,
            data=self.build_event_data(
                "day_pk_vote_tallied",
                votes=votes_snapshot,
                pk_votes=votes_snapshot,
                vote_entries=vote_entries,
                vote_counts=self._sorted_vote_counts(vote_counts),
                pk_candidate_ids=pk_candidates,
                pk_candidate_count=len(pk_candidates),
                sheriff_id=self.game.sheriff_id,
                sheriff_vote_weight=2 if self.game.sheriff_id else 1,
                abstain_voter_ids=abstain_voter_ids,
                abstain_count=len(abstain_voter_ids),
                total_ballots=len(votes_snapshot),
                counted_ballots=len(vote_entries) - len(abstain_voter_ids),
                max_votes=max_votes,
                leading_candidate_ids=list(candidates),
                pk_round=pk_round,
                outcome=self._summarize_outcome(winner_id, candidates),
            ),
        )

        self.banished_id = None

        if winner_id:
            self.banished_id = winner_id
            player = self.find_player(self.banished_id)
            if not player:
                self.add_log(
                    f"PK结果异常：未找到 {self.banished_id} 号玩家。",
                    data=self.build_event_data(
                        "day_pk_vote_result_error",
                        winner_id=self.banished_id,
                        target_id=self.banished_id,
                        max_votes=max_votes,
                        candidate_ids=list(candidates),
                        pk_candidate_ids=pk_candidates,
                        pk_round=pk_round,
                        vote_counts=self._sorted_vote_counts(vote_counts),
                        votes=votes_snapshot,
                        pk_votes=votes_snapshot,
                        outcome="error",
                        next_phase=GamePhase.NIGHT_START.value,
                        dead_player_ids=list(self.game.dead_players),
                    ),
                )
                self.banished_id = None
            else:
                player.is_alive = False
                player.death_cause = DeathCause.VOTE_EXILE
                self.game.dead_players = [self.banished_id]
                self.evaluate_win_condition()
                self.add_log(
                    f"PK结果：{self.banished_id}号玩家以{max_votes}票被放逐。",
                    data=self.build_event_data(
                        "day_pk_vote_exiled",
                        banished_id=self.banished_id,
                        winner_id=self.banished_id,
                        target_id=self.banished_id,
                        max_votes=max_votes,
                        candidate_ids=list(candidates),
                        winning_candidate_ids=list(candidates),
                        pk_candidate_ids=pk_candidates,
                        pk_round=pk_round,
                        vote_counts=self._sorted_vote_counts(vote_counts),
                        votes=votes_snapshot,
                        pk_votes=votes_snapshot,
                        dead_players=list(self.game.dead_players),
                        dead_player_ids=list(self.game.dead_players),
                        death_cause=DeathCause.VOTE_EXILE.value,
                        outcome="exiled",
                    ),
                )
        elif candidates:
            candidates_str = ", ".join([f"{pid}号" for pid in candidates])
            self.add_log(
                f"PK后仍然平票（{candidates_str}各{max_votes}票），无人出局。",
                data=self.build_event_data(
                    "day_pk_vote_tied",
                    max_votes=max_votes,
                    candidate_ids=list(candidates),
                    tied_candidate_ids=list(candidates),
                    pk_candidate_ids=pk_candidates,
                    pk_candidate_count=len(pk_candidates),
                    pk_round=pk_round,
                    vote_counts=self._sorted_vote_counts(vote_counts),
                    votes=votes_snapshot,
                    pk_votes=votes_snapshot,
                    outcome="tie_no_elimination",
                    dead_player_ids=list(self.game.dead_players),
                    next_phase=GamePhase.NIGHT_START.value,
                ),
            )
        else:
            no_elimination_reason = "all_abstained" if abstain_voter_ids else "no_ballots"
            self.add_log(
                "无人投票，无人出局。",
                data=self.build_event_data(
                    "day_pk_vote_no_elimination",
                    reason=no_elimination_reason,
                    pk_candidate_ids=pk_candidates,
                    pk_candidate_count=len(pk_candidates),
                    pk_round=pk_round,
                    vote_counts=self._sorted_vote_counts(vote_counts),
                    votes=votes_snapshot,
                    pk_votes=votes_snapshot,
                    abstain_voter_ids=abstain_voter_ids,
                    abstain_count=len(abstain_voter_ids),
                    total_ballots=len(votes_snapshot),
                    counted_ballots=0,
                    outcome="no_elimination",
                    dead_player_ids=list(self.game.dead_players),
                    next_phase=GamePhase.NIGHT_START.value,
                ),
            )

        # 清理PK状态
        self.game.pk_candidates = []
        self.game.pk_votes = {}
        self.game.pk_round = 0

    def process_action(self, action: ActionRequest) -> bool:
        return False

    def try_advance(self) -> Optional[GamePhase]:
        if self.game.winner:
            return GamePhase.GAME_END

        if hasattr(self, 'banished_id') and self.banished_id:
            skill_phase = self.check_death_skills(self.banished_id, GamePhase.NIGHT_START)
            if skill_phase:
                return skill_phase
        return GamePhase.NIGHT_START

    def _build_vote_entries(self, votes_snapshot: dict[int, int]) -> list[dict]:
        vote_entries: list[dict] = []
        for voter_id, target_id in sorted(votes_snapshot.items()):
            is_sheriff_vote = voter_id == self.game.sheriff_id
            vote_entries.append(
                {
                    "voter_id": voter_id,
                    "target_id": target_id,
                    "target_label": "弃票" if target_id == 0 else f"{target_id}号",
                    "weight": 2 if is_sheriff_vote and target_id != 0 else 1,
                    "is_sheriff_vote": is_sheriff_vote,
                }
            )
        return vote_entries

    def _sorted_vote_counts(self, vote_counts: dict[int, int]) -> dict[int, int]:
        return {candidate_id: vote_counts[candidate_id] for candidate_id in sorted(vote_counts)}

    def _summarize_outcome(self, winner_id: int | None, candidates: list[int]) -> str:
        if winner_id is not None:
            return "exile"
        if candidates:
            return "tie_no_elimination"
        return "no_elimination"
