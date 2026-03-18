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
        candidates_str = ", ".join([f"{pid}号" for pid in pk_candidates])

        self.add_log(
            f"PK投票开始。请在 {candidates_str} 中选择一人投票。PK候选人不参与投票。",
            log_type="broadcast",
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
            target_id = action.target_id
            if target_id != 0 and target_id not in self.game.pk_candidates:
                return False

            self.game.pk_votes[player.id] = target_id
            self.add_log(
                f"{player.id}号投票给 {'弃票' if target_id == 0 else f'{target_id}号'}",
                player_id=player.id,
                is_public=False,
                log_type="action",
            )
            player.has_acted = True
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
