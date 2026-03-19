"""平票PK投票阶段处理器"""
from app.core.phase_handler import PhaseHandler
from app.models.game_state import GamePhase, ActionType
from app.models.action_model import ActionRequest


class DayPKVoteHandler(PhaseHandler):
    def get_phase(self) -> GamePhase:
        return GamePhase.DAY_PK_VOTE

    def on_enter(self):
        self.game.pk_votes = {}
        pk_candidates = self.game.pk_candidates
        eligible_voter_ids = sorted(
            player.id
            for player in self.game.players
            if player.is_alive and player.id not in pk_candidates
        )
        candidates_str = ", ".join([f"{pid}号" for pid in pk_candidates])

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

        # Non-PK alive players can vote; PK candidates cannot
        for p in self.game.players:
            p.has_acted = not (p.is_alive and p.id not in pk_candidates)

    def process_action(self, action: ActionRequest) -> bool:
        player = self.find_alive_player(action.player_id)
        if not player:
            return False
        if player.id in self.game.pk_candidates:
            return False

        if action.type == ActionType.VOTE:
            target_id = 0 if action.target_id is None else action.target_id
            if target_id != 0 and target_id not in self.game.pk_candidates:
                return False

            previous_target_id = self.game.pk_votes.get(player.id)
            self.game.pk_votes[player.id] = target_id
            player.has_acted = True
            votes_snapshot = self._pk_votes_snapshot()
            eligible_players = [
                current_player
                for current_player in self.game.players
                if current_player.is_alive and current_player.id not in self.game.pk_candidates
            ]
            acted_player_ids = sorted(
                current_player.id
                for current_player in eligible_players
                if current_player.has_acted
            )
            pending_player_ids = sorted(
                current_player.id
                for current_player in eligible_players
                if not current_player.has_acted
            )
            all_acted = all(current_player.has_acted for current_player in eligible_players)
            self.add_log(
                f"{player.id}号投票给 {'弃票' if target_id == 0 else f'{target_id}号'}",
                player_id=player.id,
                is_public=False,
                log_type="action",
                data=self.build_event_data(
                    "day_pk_vote_cast",
                    action=ActionType.VOTE.value,
                    voter_id=player.id,
                    target_id=target_id,
                    target_label="弃票" if target_id == 0 else f"{target_id}号",
                    is_abstain=target_id == 0,
                    previous_target_id=previous_target_id,
                    is_update=previous_target_id is not None and previous_target_id != target_id,
                    sheriff_id=self.game.sheriff_id,
                    sheriff_vote_weight=2 if player.id == self.game.sheriff_id and target_id != 0 else 1,
                    pk_candidate_ids=list(self.game.pk_candidates),
                    pk_round=self.game.pk_round,
                    votes=votes_snapshot,
                    pk_votes=votes_snapshot,
                    votes_snapshot=votes_snapshot,
                    vote_counts=self.count_votes(votes_snapshot, sheriff_weighted=True),
                    vote_progress={
                        "acted_player_ids": acted_player_ids,
                        "pending_player_ids": pending_player_ids,
                        "acted_count": len(acted_player_ids),
                        "pending_count": len(pending_player_ids),
                        "total_eligible_voters": len(acted_player_ids) + len(pending_player_ids),
                    },
                    all_acted=all_acted,
                    next_phase_hint=GamePhase.DAY_PK_RESULT.value if all_acted else None,
                ),
            )
            return True

        return False

    def try_advance(self) -> GamePhase:
        eligible = [
            p for p in self.game.players
            if p.is_alive and p.id not in self.game.pk_candidates
        ]
        if all(p.has_acted for p in eligible):
            return GamePhase.DAY_PK_RESULT
        return None

    def _pk_votes_snapshot(self) -> dict[int, int]:
        return {int(voter_id): target_id for voter_id, target_id in self.game.pk_votes.items()}
