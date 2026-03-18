from app.core.phase_handler import PhaseHandler
from app.models.game_state import GamePhase, Role
from app.models.action_model import ActionRequest
from app.core.rules import Rules


class NightResolveHandler(PhaseHandler):
    def get_phase(self) -> GamePhase:
        return GamePhase.NIGHT_RESOLVE

    def on_enter(self):
        dead_player_ids = Rules.resolve_night_deaths(self.game)

        # 检查警长是否被毒杀（特殊规则：吞毒警徽流失）
        self.sheriff_poisoned = False
        if self.game.sheriff_id:
            sheriff = self.find_player(self.game.sheriff_id)
            if sheriff and sheriff.poisoned_by_witch:
                self.sheriff_poisoned = True
                sheriff.is_sheriff = False
                self.game.sheriff_id = None
                self.add_log("警长被毒杀，警徽流失！", log_type="broadcast")

        # Update player status
        for pid in dead_player_ids:
            player = self.find_player(pid)
            if player:
                player.is_alive = False

        self.game.dead_players = dead_player_ids

        # Reset night status for all players
        for p in self.game.players:
            p.protected_by_guard = False
            p.killed_by_wolf = False
            p.poisoned_by_witch = False
            p.saved_by_witch = False
            p.checked_by_seer = False
            p.has_acted = False

        self.game.day += 1

        self.add_log(
            f"夜晚结算完成，死亡玩家: {dead_player_ids}",
            is_public=False,
        )

    def process_action(self, action: ActionRequest) -> bool:
        return False

    def try_advance(self) -> GamePhase:
        dead_ids = self.game.dead_players

        # Identify poisoned players (died but not from wolf kill)
        poisoned_ids = [
            pid for pid in dead_ids
            if self.game.wolf_kill_target != pid
        ]

        # Check for shooters (Hunter/Wolf King not poisoned)
        for pid in dead_ids:
            player = self.find_player(pid)
            if (player and player.role in (Role.HUNTER, Role.WOLF_KING)
                    and not player.gun_used and pid not in poisoned_ids):
                self.game.next_phase_after_skill = GamePhase.DAY_START
                return GamePhase.HUNTER_SKILL

        # 警长被毒杀：警徽流失，不进入转移阶段
        if self.sheriff_poisoned:
            return GamePhase.DAY_START

        # 警长死亡（非毒杀）：需要转移警徽
        for pid in dead_ids:
            player = self.find_player(pid)
            if player and player.is_sheriff and pid not in poisoned_ids:
                self.game.next_phase_after_skill = GamePhase.DAY_START
                return GamePhase.SHERIFF_TRANSFER

        return GamePhase.DAY_START
