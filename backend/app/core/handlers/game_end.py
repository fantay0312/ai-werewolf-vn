from app.core.phase_handler import PhaseHandler
from app.models.action_model import ActionRequest
from app.models.game_state import GamePhase


class GameEndHandler(PhaseHandler):
    def get_phase(self) -> GamePhase:
        return GamePhase.GAME_END

    def on_enter(self):
        return None

    def process_action(self, action: ActionRequest) -> bool:
        return False

    def try_advance(self) -> GamePhase | None:
        return None
