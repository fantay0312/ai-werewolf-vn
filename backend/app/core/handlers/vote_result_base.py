from abc import abstractmethod
from typing import Optional

from app.core.phase_handler import PhaseHandler
from app.models.action_model import ActionRequest
from app.models.game_state import DeathCause, GamePhase


class VoteResultHandler(PhaseHandler):
    """Template for sheriff-weighted day vote resolutions."""

    votes_attribute: str
    tally_event: str
    result_event_prefix: str
    log_prefix: str = "投票结果"

    def on_enter(self):
        votes_snapshot = {
            int(voter_id): target_id
            for voter_id, target_id in getattr(self.game, self.votes_attribute).items()
        }
        vote_counts = self.count_votes(votes_snapshot, sheriff_weighted=True)
        vote_entries = self._build_vote_entries(votes_snapshot)
        abstain_voter_ids = [
            entry["voter_id"] for entry in vote_entries if entry["target_id"] == 0
        ]
        winner_id, max_votes, candidates = self.resolve_vote_winner(vote_counts)

        self.add_log(
            self.format_vote_log(votes_snapshot, prefix=self.log_prefix),
            data=self.build_event_data(
                self.tally_event,
                **self._vote_payload(votes_snapshot),
                vote_entries=vote_entries,
                vote_counts=self._sorted_vote_counts(vote_counts),
                **self._round_payload(),
                sheriff_id=self.game.sheriff_id,
                sheriff_vote_weight=2 if self.game.sheriff_id else 1,
                abstain_voter_ids=abstain_voter_ids,
                abstain_count=len(abstain_voter_ids),
                total_ballots=len(votes_snapshot),
                counted_ballots=len(vote_entries) - len(abstain_voter_ids),
                max_votes=max_votes,
                leading_candidate_ids=list(candidates),
                outcome=self._tally_outcome(winner_id, candidates),
            ),
        )

        self.banished_id = None
        if winner_id is not None:
            self._resolve_exile(winner_id, max_votes, candidates, vote_counts, votes_snapshot)
        elif candidates:
            self._resolve_tie(max_votes, candidates, vote_counts, votes_snapshot)
        else:
            self._resolve_no_elimination(abstain_voter_ids, vote_counts, votes_snapshot)
        self._cleanup()

    def process_action(self, action: ActionRequest) -> bool:
        return False

    def try_advance(self) -> Optional[GamePhase]:
        banished_id = self._resolved_exile_id()
        if banished_id:
            skill_phase = self.check_death_skills(banished_id, GamePhase.NIGHT_START)
            if skill_phase:
                self.game.winner = None
                return skill_phase
        if self.game.winner:
            return GamePhase.GAME_END
        return self._next_phase()

    def _resolve_exile(self, winner_id, max_votes, candidates, vote_counts, votes_snapshot):
        self.banished_id = winner_id
        player = self.find_player(winner_id)
        if not player:
            self.add_log(
                self._error_content(winner_id),
                data=self.build_event_data(
                    f"{self.result_event_prefix}_result_error",
                    winner_id=winner_id,
                    target_id=winner_id,
                    max_votes=max_votes,
                    candidate_ids=list(candidates),
                    **self._round_payload(),
                    vote_counts=self._sorted_vote_counts(vote_counts),
                    **self._vote_payload(votes_snapshot),
                    outcome="error",
                    next_phase=GamePhase.NIGHT_START.value,
                    dead_player_ids=list(self.game.dead_players),
                ),
            )
            self.banished_id = None
            return

        self.record_death(player, DeathCause.VOTE_EXILE)
        self.game.dead_players = [winner_id]
        self.evaluate_win_condition()
        self.add_log(
            self._exile_content(winner_id, max_votes),
            data=self.build_event_data(
                f"{self.result_event_prefix}_exiled",
                banished_id=winner_id,
                winner_id=winner_id,
                target_id=winner_id,
                max_votes=max_votes,
                candidate_ids=list(candidates),
                winning_candidate_ids=list(candidates),
                **self._round_payload(),
                vote_counts=self._sorted_vote_counts(vote_counts),
                **self._vote_payload(votes_snapshot),
                dead_players=list(self.game.dead_players),
                dead_player_ids=list(self.game.dead_players),
                death_cause=DeathCause.VOTE_EXILE.value,
                outcome="exiled",
            ),
        )

    def _resolve_no_elimination(self, abstain_voter_ids, vote_counts, votes_snapshot):
        reason = "all_abstained" if abstain_voter_ids else "no_ballots"
        self.add_log(
            "无人投票，无人出局。",
            data=self.build_event_data(
                f"{self.result_event_prefix}_no_elimination",
                reason=reason,
                **self._round_payload(),
                vote_counts=self._sorted_vote_counts(vote_counts),
                **self._vote_payload(votes_snapshot),
                abstain_voter_ids=abstain_voter_ids,
                abstain_count=len(abstain_voter_ids),
                total_ballots=len(votes_snapshot),
                counted_ballots=0,
                outcome="no_elimination",
                dead_player_ids=list(self.game.dead_players),
                next_phase=GamePhase.NIGHT_START.value,
            ),
        )

    def _build_vote_entries(self, votes_snapshot: dict[int, int]) -> list[dict]:
        return [
            {
                "voter_id": voter_id,
                "target_id": target_id,
                "target_label": "弃票" if target_id == 0 else f"{target_id}号",
                "weight": 2 if voter_id == self.game.sheriff_id and target_id != 0 else 1,
                "is_sheriff_vote": voter_id == self.game.sheriff_id,
            }
            for voter_id, target_id in sorted(votes_snapshot.items())
        ]

    @staticmethod
    def _sorted_vote_counts(vote_counts: dict[int, int]) -> dict[int, int]:
        return {candidate_id: vote_counts[candidate_id] for candidate_id in sorted(vote_counts)}

    def _vote_payload(self, votes_snapshot: dict[int, int]) -> dict:
        return {"votes": votes_snapshot}

    def _round_payload(self) -> dict:
        return {}

    def _tally_outcome(self, winner_id: int | None, candidates: list[int]) -> str:
        if winner_id is not None:
            return "exile"
        if candidates:
            return self._tie_outcome()
        return "no_elimination"

    def _cleanup(self) -> None:
        pass

    @abstractmethod
    def _resolve_tie(self, max_votes, candidates, vote_counts, votes_snapshot) -> None:
        pass

    @abstractmethod
    def _tie_outcome(self) -> str:
        pass

    @abstractmethod
    def _error_content(self, winner_id: int) -> str:
        pass

    @abstractmethod
    def _exile_content(self, winner_id: int, max_votes: int) -> str:
        pass

    def _next_phase(self) -> GamePhase:
        return GamePhase.NIGHT_START

    def _resolved_exile_id(self) -> int | None:
        player = next(
            (
                player for player in self.game.players
                if player.id in self.game.dead_players
                and player.death_phase == self.game.phase
                and player.death_cause == DeathCause.VOTE_EXILE
            ),
            None,
        )
        return player.id if player else None
