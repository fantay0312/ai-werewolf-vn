"""平票PK发言阶段处理器"""
from app.core.phase_handler import PhaseHandler
from app.models.game_state import GamePhase, ActionType, GameLog
from app.models.action_model import ActionRequest
import uuid


class DayPKSpeechHandler(PhaseHandler):
    def get_phase(self) -> GamePhase:
        return GamePhase.DAY_PK_SPEECH

    def on_enter(self):
        # 获取PK候选人
        pk_candidates = sorted(self.game.pk_candidates)

        if not pk_candidates:
            return

        candidates_str = ", ".join([f"{pid}号" for pid in pk_candidates])
        content = f"进入平票PK环节。PK玩家：{candidates_str}。请依次发表PK发言。"

        log = GameLog(
            id=str(uuid.uuid4()),
            day=self.game.day,
            phase=self.game.phase,
            content=content,
            is_public=True,
            type="broadcast"
        )
        self.game.game_logs.append(log)

        # 设置发言顺序
        self.game.speaking_order = pk_candidates
        self.game.current_speaker_index = 0

        # 重置PK候选人的行动状态
        for pid in pk_candidates:
            player = next((p for p in self.game.players if p.id == pid), None)
            if player:
                player.has_acted = False

    def process_action(self, action: ActionRequest) -> bool:
        # 检查是否是当前发言者
        if not self.game.speaking_order:
            return False

        if self.game.current_speaker_index >= len(self.game.speaking_order):
            return False

        current_speaker_id = self.game.speaking_order[self.game.current_speaker_index]
        if action.player_id != current_speaker_id:
            return False

        player = next((p for p in self.game.players if p.id == action.player_id), None)
        if not player:
            return False

        if action.type == ActionType.SPEECH:
            log = GameLog(
                id=str(uuid.uuid4()),
                day=self.game.day,
                phase=self.game.phase,
                content=f"{player.id}号(PK发言): {action.content}",
                player_id=player.id,
                is_public=True,
                type="speech"
            )
            self.game.game_logs.append(log)
            player.has_acted = True
            self._advance_speaker()
            return True

        elif action.type == ActionType.CONFIRM:
            # 跳过发言
            player.has_acted = True
            self._advance_speaker()
            return True

        return False

    def _advance_speaker(self):
        self.game.current_speaker_index += 1

    def try_advance(self) -> GamePhase:
        # 所有PK候选人发言完毕
        if self.game.current_speaker_index >= len(self.game.speaking_order):
            return GamePhase.DAY_PK_VOTE
        return None
