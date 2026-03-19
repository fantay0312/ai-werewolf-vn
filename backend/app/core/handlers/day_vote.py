from app.core.phase_handler import PhaseHandler
from app.models.game_state import GamePhase, ActionType
from app.models.action_model import ActionRequest


class DayVoteHandler(PhaseHandler):
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

    def process_action(self, action: ActionRequest) -> bool:
        player = self.find_alive_player(action.player_id)
        if not player:
            return False

        if action.type == ActionType.VOTE:
            try:
                target_id = 0 if action.target_id is None else int(action.target_id)
            except (ValueError, TypeError):
                return False
            if target_id != 0 and not self.is_alive_target(target_id):
                return False
            previous_target_id = self.game.votes.get(player.id)
            self.game.votes[player.id] = target_id
            player.has_acted = True
            votes_snapshot = self._votes_snapshot()
            acted_player_ids = sorted(
                current_player.id
                for current_player in self.get_alive_players()
                if current_player.has_acted
            )
            pending_player_ids = sorted(
                current_player.id
                for current_player in self.get_alive_players()
                if not current_player.has_acted
            )
            self.add_log(
                f"{player.id}号玩家完成投票。",
                player_id=player.id,
                log_type="action",
                data=self.build_event_data(
                    "day_vote_cast",
                    action=ActionType.VOTE.value,
                    voter_id=player.id,
                    target_id=target_id,
                    target_label="弃票" if target_id == 0 else f"{target_id}号",
                    is_abstain=target_id == 0,
                    previous_target_id=previous_target_id,
                    is_update=previous_target_id is not None and previous_target_id != target_id,
                    sheriff_id=self.game.sheriff_id,
                    sheriff_vote_weight=2 if player.id == self.game.sheriff_id and target_id != 0 else 1,
                    votes=votes_snapshot,
                    votes_snapshot=votes_snapshot,
                    vote_counts=self.count_votes(votes_snapshot, sheriff_weighted=True),
                    vote_progress={
                        "acted_player_ids": acted_player_ids,
                        "pending_player_ids": pending_player_ids,
                        "acted_count": len(acted_player_ids),
                        "pending_count": len(pending_player_ids),
                        "total_eligible_voters": len(acted_player_ids) + len(pending_player_ids),
                    },
                    all_acted=self.all_acted(),
                    next_phase_hint=GamePhase.DAY_VOTE_RESULT.value if self.all_acted() else None,
                ),
            )
            return True

        return False

    def try_advance(self) -> GamePhase:
        if self.all_acted():
            return GamePhase.DAY_VOTE_RESULT
        return None

    def _votes_snapshot(self) -> dict[int, int]:
        return {int(voter_id): target_id for voter_id, target_id in self.game.votes.items()}
