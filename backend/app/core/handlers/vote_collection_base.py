from abc import abstractmethod

from app.core.phase_handler import PhaseHandler
from app.models.action_model import ActionRequest
from app.models.game_state import ActionType, GamePhase, Player


class VoteCollectionHandler(PhaseHandler):
    """Common collection and progress logging for day ballots."""

    votes_attribute: str
    cast_event: str
    result_phase: GamePhase

    def process_action(self, action: ActionRequest) -> bool:
        player = self.find_alive_player(action.player_id)
        if not player or not self._is_eligible_voter(player):
            return False
        if action.type != ActionType.VOTE:
            return False

        try:
            target_id = 0 if action.target_id is None else int(action.target_id)
        except (ValueError, TypeError):
            return False
        if target_id != 0 and not self._is_eligible_target(target_id):
            return False

        votes = getattr(self.game, self.votes_attribute)
        previous_target_id = votes.get(player.id)
        votes[player.id] = target_id
        player.has_acted = True

        votes_snapshot = self._votes_snapshot()
        eligible_players = self._eligible_voters()
        acted_player_ids = sorted(p.id for p in eligible_players if p.has_acted)
        pending_player_ids = sorted(p.id for p in eligible_players if not p.has_acted)
        all_acted = not pending_player_ids
        self.add_log(
            self._cast_content(player, target_id),
            player_id=player.id,
            is_public=False,
            log_type="action",
            data=self.build_event_data(
                self.cast_event,
                action=ActionType.VOTE.value,
                voter_id=player.id,
                target_id=target_id,
                target_label="弃票" if target_id == 0 else f"{target_id}号",
                is_abstain=target_id == 0,
                previous_target_id=previous_target_id,
                is_update=previous_target_id is not None and previous_target_id != target_id,
                sheriff_id=self.game.sheriff_id,
                sheriff_vote_weight=2 if player.id == self.game.sheriff_id and target_id != 0 else 1,
                **self._vote_payload(votes_snapshot),
                vote_counts=self.count_votes(votes_snapshot, sheriff_weighted=True),
                vote_progress={
                    "acted_player_ids": acted_player_ids,
                    "pending_player_ids": pending_player_ids,
                    "acted_count": len(acted_player_ids),
                    "pending_count": len(pending_player_ids),
                    "total_eligible_voters": len(eligible_players),
                },
                all_acted=all_acted,
                next_phase_hint=self.result_phase.value if all_acted else None,
            ),
        )
        return True

    def try_advance(self) -> GamePhase | None:
        if all(player.has_acted for player in self._eligible_voters()):
            return self.result_phase
        return None

    def _votes_snapshot(self) -> dict[int, int]:
        return {
            int(voter_id): target_id
            for voter_id, target_id in getattr(self.game, self.votes_attribute).items()
        }

    def _vote_payload(self, votes_snapshot: dict[int, int]) -> dict:
        return {"votes": votes_snapshot, "votes_snapshot": votes_snapshot}

    def _is_eligible_voter(self, player: Player) -> bool:
        return player in self._eligible_voters()

    @abstractmethod
    def _eligible_voters(self) -> list[Player]:
        pass

    @abstractmethod
    def _is_eligible_target(self, target_id: int) -> bool:
        pass

    @abstractmethod
    def _cast_content(self, player: Player, target_id: int) -> str:
        pass
