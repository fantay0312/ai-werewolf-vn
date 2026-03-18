from app.core.phase_handler import PhaseHandler
from app.models.game_state import GamePhase
from app.models.action_model import ActionRequest


class NightStartHandler(PhaseHandler):
    def get_phase(self) -> GamePhase:
        return GamePhase.NIGHT_START

    def on_enter(self):
        self.add_log(f"第{self.game.day}夜，天黑请闭眼。")

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
        return False

    def try_advance(self) -> GamePhase:
        return GamePhase.NIGHT_WOLF_DISCUSS
