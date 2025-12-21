from app.core.phase_handler import PhaseHandler
from app.models.game_state import GamePhase, ActionType, GameLog
from app.models.action_model import ActionRequest
import uuid

class GameStartHandler(PhaseHandler):
    def get_phase(self) -> GamePhase:
        return GamePhase.GAME_START

    def on_enter(self):
        # Announce game start
        log = GameLog(
            id=str(uuid.uuid4()),
            day=self.game.day,
            phase=self.game.phase,
            content="游戏开始！请确认您的身份。",
            is_public=True
        )
        self.game.game_logs.append(log)
        
        # Reset all player states
        for p in self.game.players:
            p.has_acted = False

    def process_action(self, action: ActionRequest) -> bool:
        if action.type in [ActionType.CONFIRM, ActionType.PASS]:
            player = next((p for p in self.game.players if p.id == action.player_id), None)
            if player:
                player.has_acted = True
                return True
        return False

    def try_advance(self) -> GamePhase:
        human = next((p for p in self.game.players if p.is_human), None)
        if human and human.has_acted:
            return GamePhase.SHERIFF_ELECTION
        return None