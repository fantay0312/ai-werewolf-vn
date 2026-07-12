from typing import Optional
from app.core.phase_handler import PhaseHandler
from app.models.game_state import DeathCause, GamePhase
from app.models.action_model import ActionRequest


class DayVoteResultHandler(PhaseHandler):
    def get_phase(self) -> GamePhase:
        return GamePhase.DAY_VOTE_RESULT

    def on_enter(self):
        votes_snapshot = {int(k): v for k, v in self.game.votes.items()}
        vote_counts = self.count_votes(votes_snapshot, sheriff_weighted=True)
        vote_entries = self._build_vote_entries(votes_snapshot)
        abstain_voter_ids = [entry["voter_id"] for entry in vote_entries if entry["target_id"] == 0]
        winner_id, max_votes, candidates = self.resolve_vote_winner(vote_counts)

        # Log vote details
        content = self.format_vote_log(votes_snapshot)
        self.add_log(
            content,
            data=self.build_event_data(
                "day_vote_tallied",
                votes=votes_snapshot,
                vote_entries=vote_entries,
                vote_counts=self._sorted_vote_counts(vote_counts),
                sheriff_id=self.game.sheriff_id,
                sheriff_vote_weight=2 if self.game.sheriff_id else 1,
                abstain_voter_ids=abstain_voter_ids,
                abstain_count=len(abstain_voter_ids),
                total_ballots=len(votes_snapshot),
                counted_ballots=len(vote_entries) - len(abstain_voter_ids),
                max_votes=max_votes,
                leading_candidate_ids=list(candidates),
                outcome=self._summarize_outcome(winner_id, candidates),
            ),
        )

        # Determine banished player
        self.banished_id = None

        if winner_id:
            self.banished_id = winner_id
            player = self.find_player(self.banished_id)
            if not player:
                self.add_log(
                    f"投票结果异常：未找到 {self.banished_id} 号玩家。",
                    data=self.build_event_data(
                        "day_vote_result_error",
                        winner_id=self.banished_id,
                        target_id=self.banished_id,
                        max_votes=max_votes,
                        candidate_ids=list(candidates),
                        vote_counts=self._sorted_vote_counts(vote_counts),
                        votes=votes_snapshot,
                        outcome="error",
                        next_phase=GamePhase.NIGHT_START.value,
                        dead_player_ids=list(self.game.dead_players),
                    ),
                )
                return
            player.is_alive = False
            player.death_cause = DeathCause.VOTE_EXILE
            self.game.dead_players = [self.banished_id]
            self.evaluate_win_condition()
            self.add_log(
                f"{self.banished_id}号玩家以{max_votes}票被放逐。",
                data=self.build_event_data(
                    "day_vote_exiled",
                    banished_id=self.banished_id,
                    winner_id=self.banished_id,
                    target_id=self.banished_id,
                    max_votes=max_votes,
                    candidate_ids=list(candidates),
                    winning_candidate_ids=list(candidates),
                    vote_counts=self._sorted_vote_counts(vote_counts),
                    votes=votes_snapshot,
                    dead_players=list(self.game.dead_players),
                    dead_player_ids=list(self.game.dead_players),
                    death_cause=DeathCause.VOTE_EXILE.value,
                    outcome="exiled",
                ),
            )
        elif candidates:
            # 平票 - 进入PK环节
            candidates_str = ", ".join([f"{pid}号" for pid in candidates])
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
        else:
            no_elimination_reason = "all_abstained" if abstain_voter_ids else "no_ballots"
            self.add_log(
                "无人投票，无人出局。",
                data=self.build_event_data(
                    "day_vote_no_elimination",
                    reason=no_elimination_reason,
                    vote_counts=self._sorted_vote_counts(vote_counts),
                    votes=votes_snapshot,
                    abstain_voter_ids=abstain_voter_ids,
                    abstain_count=len(abstain_voter_ids),
                    total_ballots=len(votes_snapshot),
                    counted_ballots=0,
                    outcome="no_elimination",
                    dead_player_ids=list(self.game.dead_players),
                    next_phase=GamePhase.NIGHT_START.value,
                ),
            )

    def process_action(self, action: ActionRequest) -> bool:
        return False

    def try_advance(self) -> Optional[GamePhase]:
        if self.game.winner:
            return GamePhase.GAME_END

        if hasattr(self, 'banished_id') and self.banished_id:
            skill_phase = self.check_death_skills(self.banished_id, GamePhase.NIGHT_START)
            if skill_phase:
                return skill_phase

        if hasattr(self, 'need_pk') and self.need_pk:
            return GamePhase.DAY_PK_SPEECH

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
            return "tie"
        return "no_elimination"
