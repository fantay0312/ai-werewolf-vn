from app.core.phase_handler import PhaseHandler
from app.models.game_state import GamePhase, ActionType
from app.models.action_model import ActionRequest


class GameStartHandler(PhaseHandler):
    def get_phase(self) -> GamePhase:
        return GamePhase.GAME_START

    def on_enter(self):
        self.add_log("游戏开始！请确认您的身份。")
        self.reset_actions()

    def process_action(self, action: ActionRequest) -> bool:
        if action.type in (ActionType.CONFIRM, ActionType.PASS):
            player = self.find_player(action.player_id)
            if player:
                player.has_acted = True
                return True
        return False

    def try_advance(self) -> GamePhase:
        human = next((p for p in self.game.players if p.is_human), None)
        if human and human.has_acted:
            return GamePhase.SHERIFF_ELECTION
        return None
