from app.core.phase_handler import PhaseHandler
from app.models.game_state import GamePhase, ActionType, GameLog, Role
from app.models.action_model import ActionRequest
from app.core.rules import Rules
import uuid


class NightResolveHandler(PhaseHandler):
    def get_phase(self) -> GamePhase:
        return GamePhase.NIGHT_RESOLVE

    def on_enter(self):
        # Calculate deaths using Rules engine
        dead_player_ids = Rules.resolve_night_deaths(self.game)

        # 检查警长是否被毒杀（特殊规则：吞毒警徽流失）
        self.sheriff_poisoned = False
        if self.game.sheriff_id:
            sheriff = next((p for p in self.game.players if p.id == self.game.sheriff_id), None)
            if sheriff and sheriff.poisoned_by_witch:
                self.sheriff_poisoned = True
                # 警徽直接流失
                sheriff.is_sheriff = False
                self.game.sheriff_id = None

                log = GameLog(
                    id=str(uuid.uuid4()),
                    day=self.game.day,
                    phase=self.game.phase,
                    content="警长被毒杀，警徽流失！",
                    is_public=True,
                    type="broadcast"
                )
                self.game.game_logs.append(log)

        # Update player status
        for pid in dead_player_ids:
            player = next((p for p in self.game.players if p.id == pid), None)
            if player:
                player.is_alive = False

        # Store dead players in game state for Day Start announcement
        self.game.dead_players = dead_player_ids

        # Reset night status for all players
        for p in self.game.players:
            p.protected_by_guard = False
            p.killed_by_wolf = False
            p.poisoned_by_witch = False
            p.saved_by_witch = False
            p.checked_by_seer = False
            p.has_acted = False

        # Increment day counter
        self.game.day += 1

        # Log resolution (internal)
        log = GameLog(
            id=str(uuid.uuid4()),
            day=self.game.day,
            phase=self.game.phase,
            content=f"夜晚结算完成，死亡玩家: {dead_player_ids}",
            is_public=False
        )
        self.game.game_logs.append(log)

    def process_action(self, action: ActionRequest) -> bool:
        return False

    def try_advance(self) -> GamePhase:
        dead_ids = self.game.dead_players

        # 检查是否有猎人/狼王死亡需要发动技能
        shooters = []
        for pid in dead_ids:
            player = next((p for p in self.game.players if p.id == pid), None)
            if player and player.role in [Role.HUNTER, Role.WOLF_KING]:
                # 被毒杀的猎人/狼王不能开枪
                if not getattr(self, '_player_was_poisoned', {}).get(pid, False):
                    # 检查是否已经开过枪
                    if not player.gun_used:
                        shooters.append(player)

        # 检查猎人/狼王是否被毒杀（需要从on_enter中传递这个信息）
        # 简化处理：如果是女巫毒杀则不能开枪
        poisoned_ids = []
        for pid in dead_ids:
            player = next((p for p in self.game.players if p.id == pid), None)
            # 如果只死了一个人且没有被狼人刀，那就是被毒杀
            if player and self.game.wolf_kill_target != pid:
                poisoned_ids.append(pid)

        # 过滤掉被毒杀的
        shooters = [s for s in shooters if s.id not in poisoned_ids]

        # 检查警长是否死亡（非毒杀情况需要传递警徽）
        sheriff_died = self.game.sheriff_id is None and hasattr(self, 'sheriff_poisoned') and not self.sheriff_poisoned
        # 更准确的判断：检查原警长是否在死亡名单中且不是被毒杀
        for pid in dead_ids:
            player = next((p for p in self.game.players if p.id == pid), None)
            if player and player.is_sheriff and pid not in poisoned_ids:
                sheriff_died = True
                break

        # Determine next phase
        if shooters:
            self.game.next_phase_after_skill = GamePhase.DAY_START
            return GamePhase.HUNTER_SKILL

        # 警长被毒杀：警徽流失，不进入转移阶段
        if hasattr(self, 'sheriff_poisoned') and self.sheriff_poisoned:
            # 吞毒警徽流失，直接进入白天
            return GamePhase.DAY_START

        # 警长死亡（非毒杀）：需要转移警徽
        if sheriff_died:
            self.game.next_phase_after_skill = GamePhase.DAY_START
            return GamePhase.SHERIFF_TRANSFER

        return GamePhase.DAY_START
