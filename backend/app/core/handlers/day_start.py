from app.core.phase_handler import PhaseHandler
from app.models.game_state import GamePhase, ActionType
from app.models.action_model import ActionRequest
from app.core.rules import Rules


class DayStartHandler(PhaseHandler):
    def get_phase(self) -> GamePhase:
        return GamePhase.DAY_START

    def on_enter(self):
        dead_ids = self.game.dead_players
        if not dead_ids:
            content = "天亮了。昨晚是平安夜。"
        else:
            dead_str = ", ".join([f"{pid}号" for pid in dead_ids])
            content = f"天亮了。昨晚死亡的是 {dead_str}。"

        self.add_log(content)

        winner = Rules.check_win_condition(self.game)
        if winner:
            self.game.winner = winner

    def process_action(self, action: ActionRequest) -> bool:
        if action.type == ActionType.CONFIRM:
            player = self.find_player(action.player_id)
            if player:
                player.has_acted = True
                return True
        return False

    def try_advance(self) -> GamePhase:
        if self.game.winner:
            return GamePhase.GAME_END

        if self.game.day == 1 and self.game.dead_players:
            return GamePhase.DAY_LAST_WORDS

        if self.game.election_cancelled:
            return GamePhase.DAY_DISCUSS

        if self.game.day == 1 or self.game.pending_sheriff_election:
            if self.game.pending_sheriff_election:
                self.game.pending_sheriff_election = False
            return GamePhase.SHERIFF_ELECTION

        return GamePhase.DAY_DISCUSS
