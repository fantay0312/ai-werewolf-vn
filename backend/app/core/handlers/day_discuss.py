from app.core.phase_handler import PhaseHandler
from app.models.game_state import GamePhase, ActionType
from app.models.action_model import ActionRequest


class DayDiscussHandler(PhaseHandler):
    def get_phase(self) -> GamePhase:
        return GamePhase.DAY_DISCUSS

    def on_enter(self):
        alive_ids = [p.id for p in self.game.players if p.is_alive]
        speaking_order = self.gm.judge_system.determine_speaking_order(
            alive_ids, self.game.sheriff_id
        )
        self.game.speaking_order = speaking_order
        self.game.current_speaker_index = 0

        order_str = ", ".join([f"{pid}号" for pid in speaking_order])
        self.add_log(f"现在开始自由讨论。发言顺序：{order_str}")
        self.reset_actions()

    def process_action(self, action: ActionRequest) -> bool:
        player = self.find_alive_player(action.player_id)
        if not player:
            return False

        if action.type == ActionType.SPEECH:
            self.add_log(
                f"{player.id}号: {action.content}",
                player_id=player.id,
            )
            player.has_acted = True
            return True

        if action.type in (ActionType.CONFIRM, ActionType.PASS):
            player.has_acted = True
            return True

        return False

    def try_advance(self) -> GamePhase:
        if self.all_acted():
            return GamePhase.DAY_VOTE
        return None
