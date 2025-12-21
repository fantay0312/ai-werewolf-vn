from app.core.phase_handler import PhaseHandler
from app.models.game_state import GamePhase, ActionType, GameLog, Role
from app.models.action_model import ActionRequest
from app.core.rules import Rules
import uuid

class DayStartHandler(PhaseHandler):
    def get_phase(self) -> GamePhase:
        return GamePhase.DAY_START

    def on_enter(self):
        # Announce deaths
        dead_ids = self.game.dead_players
        if not dead_ids:
            content = "天亮了。昨晚是平安夜。"
        else:
            dead_str = ", ".join([f"{pid}号" for pid in dead_ids])
            content = f"天亮了。昨晚死亡的是 {dead_str}。"
            
        log = GameLog(
            id=str(uuid.uuid4()),
            day=self.game.day,
            phase=self.game.phase,
            content=content,
            is_public=True
        )
        self.game.game_logs.append(log)
        
        # Check win condition immediately after deaths
        winner = Rules.check_win_condition(self.game)
        if winner:
            self.game.winner = winner
            # Game End Logic will be handled by GameEndHandler or similar check

    def process_action(self, action: ActionRequest) -> bool:
        # Wait for confirmation/acknowledgment?
        if action.type == ActionType.CONFIRM:
            player = next((p for p in self.game.players if p.id == action.player_id), None)
            if player:
                player.has_acted = True
                return True
        return False

    def try_advance(self) -> GamePhase:
        if self.game.winner:
            return GamePhase.GAME_END

        # 第一天有死亡玩家时，进入遗言阶段
        if self.game.day == 1 and self.game.dead_players:
            return GamePhase.DAY_LAST_WORDS

        # 检查竞选是否已被双自爆取消
        if self.game.election_cancelled:
            return GamePhase.DAY_DISCUSS

        # If Day 1 or pending election, go to Sheriff Election
        if self.game.day == 1 or self.game.pending_sheriff_election:
            # Reset pending flag if we are entering election
            if self.game.pending_sheriff_election:
                self.game.pending_sheriff_election = False
            return GamePhase.SHERIFF_ELECTION

        return GamePhase.DAY_DISCUSS