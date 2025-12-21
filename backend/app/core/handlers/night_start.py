from app.core.phase_handler import PhaseHandler
from app.models.game_state import GamePhase, ActionType, GameLog
from app.models.action_model import ActionRequest
import uuid

class NightStartHandler(PhaseHandler):
    def get_phase(self) -> GamePhase:
        return GamePhase.NIGHT_START

    def on_enter(self):
        # Announce night start
        log = GameLog(
            id=str(uuid.uuid4()),
            day=self.game.day,
            phase=self.game.phase,
            content=f"第{self.game.day}夜，天黑请闭眼。",
            is_public=True
        )
        self.game.game_logs.append(log)

        # Reset nightly states
        self.game.wolf_kill_target = None
        self.game.votes = {}
        self.game.wolf_discuss_messages = []
        for p in self.game.players:
            p.has_acted = False
            p.protected_by_guard = False
            p.killed_by_wolf = False
            p.poisoned_by_witch = False
            p.saved_by_witch = False
            p.checked_by_seer = False

    def process_action(self, action: ActionRequest) -> bool:
        # Auto-advance, no actions needed
        return False

    def try_advance(self) -> GamePhase:
        # Immediately advance to Wolf Discussion
        return GamePhase.NIGHT_WOLF_DISCUSS