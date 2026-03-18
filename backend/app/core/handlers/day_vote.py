from app.core.phase_handler import PhaseHandler
from app.models.game_state import GamePhase, ActionType
from app.models.action_model import ActionRequest


class DayVoteHandler(PhaseHandler):
    def get_phase(self) -> GamePhase:
        return GamePhase.DAY_VOTE

    def on_enter(self):
        self.add_log("请投票放逐一名玩家。")
        self.game.votes = {}
        self.reset_actions()

    def process_action(self, action: ActionRequest) -> bool:
        player = self.find_alive_player(action.player_id)
        if not player:
            return False

        if action.type == ActionType.VOTE:
            try:
                target_id = 0 if action.target_id is None else int(action.target_id)
            except (ValueError, TypeError):
                return False
            self.game.votes[player.id] = target_id
            player.has_acted = True
            return True

        return False

    def try_advance(self) -> GamePhase:
        if self.all_acted():
            return GamePhase.DAY_VOTE_RESULT
        return None
