"""平票PK结果阶段处理器"""
from typing import Optional
from app.core.phase_handler import PhaseHandler
from app.models.game_state import GamePhase, ActionType, GameLog, Role
from app.models.action_model import ActionRequest
from app.core.rules import Rules
import uuid


class DayPKResultHandler(PhaseHandler):
    def get_phase(self) -> GamePhase:
        return GamePhase.DAY_PK_RESULT

    def on_enter(self):
        # 统计PK投票（警长票权依然2倍）
        vote_counts = {}
        sheriff_id = self.game.sheriff_id

        content = "PK投票结果：\n"
        for voter_id, target_id in self.game.pk_votes.items():
            weight = 2 if voter_id == sheriff_id else 1
            weight_str = "(警长票x2)" if voter_id == sheriff_id else ""

            target_name = f"{target_id}号" if target_id != 0 else "弃票"
            content += f"{voter_id}号{weight_str} -> {target_name}\n"

            if target_id != 0:
                if target_id not in vote_counts:
                    vote_counts[target_id] = 0
                vote_counts[target_id] += weight

        log = GameLog(
            id=str(uuid.uuid4()),
            day=self.game.day,
            phase=self.game.phase,
            content=content,
            is_public=True,
            data={"pk_votes": self.game.pk_votes, "sheriff_id": sheriff_id}
        )
        self.game.game_logs.append(log)

        # 决定出局玩家
        self.banished_id = None

        if vote_counts:
            max_votes = max(vote_counts.values())
            candidates = [pid for pid, c in vote_counts.items() if c == max_votes]

            if len(candidates) == 1:
                # 有明确结果
                self.banished_id = candidates[0]
                player = next(p for p in self.game.players if p.id == self.banished_id)
                player.is_alive = False
                self.game.dead_players.append(self.banished_id)

                log = GameLog(
                    id=str(uuid.uuid4()),
                    day=self.game.day,
                    phase=self.game.phase,
                    content=f"PK结果：{self.banished_id}号玩家以{max_votes}票被放逐。",
                    is_public=True
                )
                self.game.game_logs.append(log)
            else:
                # PK后仍然平票，无人出局
                candidates_str = ", ".join([f"{pid}号" for pid in candidates])
                log = GameLog(
                    id=str(uuid.uuid4()),
                    day=self.game.day,
                    phase=self.game.phase,
                    content=f"PK后仍然平票（{candidates_str}各{max_votes}票），无人出局。",
                    is_public=True
                )
                self.game.game_logs.append(log)
        else:
            log = GameLog(
                id=str(uuid.uuid4()),
                day=self.game.day,
                phase=self.game.phase,
                content="无人投票，无人出局。",
                is_public=True
            )
            self.game.game_logs.append(log)

        # 清理PK状态
        self.game.pk_candidates = []
        self.game.pk_votes = {}
        self.game.pk_round = 0

    def process_action(self, action: ActionRequest) -> bool:
        return False

    def try_advance(self) -> Optional[GamePhase]:
        # 检查死亡技能
        if hasattr(self, 'banished_id') and self.banished_id:
            player = next(p for p in self.game.players if p.id == self.banished_id)

            # 检查猎人/狼王
            if player.role in [Role.HUNTER, Role.WOLF_KING]:
                if Rules.can_shoot(player, "vote"):
                    self.game.next_phase_after_skill = GamePhase.NIGHT_START
                    return GamePhase.HUNTER_SKILL

            # 检查警长
            if player.is_sheriff:
                self.game.next_phase_after_skill = GamePhase.NIGHT_START
                return GamePhase.SHERIFF_TRANSFER

        # 进入夜晚
        return GamePhase.NIGHT_START
