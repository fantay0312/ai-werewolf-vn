"""平票PK投票阶段处理器"""
from app.core.phase_handler import PhaseHandler
from app.models.game_state import GamePhase, ActionType, GameLog
from app.models.action_model import ActionRequest
import uuid


class DayPKVoteHandler(PhaseHandler):
    def get_phase(self) -> GamePhase:
        return GamePhase.DAY_PK_VOTE

    def on_enter(self):
        # 清空PK投票
        self.game.pk_votes = {}

        pk_candidates = self.game.pk_candidates
        candidates_str = ", ".join([f"{pid}号" for pid in pk_candidates])

        log = GameLog(
            id=str(uuid.uuid4()),
            day=self.game.day,
            phase=self.game.phase,
            content=f"PK投票开始。请在 {candidates_str} 中选择一人投票。PK候选人不参与投票。",
            is_public=True,
            type="broadcast"
        )
        self.game.game_logs.append(log)

        # 重置非PK玩家的行动状态（只有他们可以投票）
        for p in self.game.players:
            if p.is_alive and p.id not in pk_candidates:
                p.has_acted = False
            else:
                p.has_acted = True  # PK候选人不参与投票

    def process_action(self, action: ActionRequest) -> bool:
        player = next((p for p in self.game.players if p.id == action.player_id), None)
        if not player or not player.is_alive:
            return False

        # PK候选人不能投票
        if player.id in self.game.pk_candidates:
            return False

        if action.type == ActionType.VOTE:
            target_id = action.target_id

            # 验证目标是否是PK候选人或弃票(0)
            if target_id != 0 and target_id not in self.game.pk_candidates:
                return False

            self.game.pk_votes[player.id] = target_id

            # 记录投票日志
            target_name = f"{target_id}号" if target_id != 0 else "弃票"
            log = GameLog(
                id=str(uuid.uuid4()),
                day=self.game.day,
                phase=self.game.phase,
                content=f"{player.id}号投票给 {target_name}",
                player_id=player.id,
                is_public=False,  # 暗票
                type="action"
            )
            self.game.game_logs.append(log)

            player.has_acted = True
            return True

        return False

    def try_advance(self) -> GamePhase:
        # 检查所有非PK玩家是否都已投票
        eligible_voters = [
            p for p in self.game.players
            if p.is_alive and p.id not in self.game.pk_candidates
        ]

        if all(p.has_acted for p in eligible_voters):
            return GamePhase.DAY_PK_RESULT

        return None
