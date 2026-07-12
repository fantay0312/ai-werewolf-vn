from app.core.handlers.turn_window import TurnWindowHandler
from app.models.action_model import ActionRequest
from app.models.game_state import GamePhase, Player


class DayDiscussHandler(TurnWindowHandler):
    speech_event = "day_discuss_speech"
    turn_end_event = "day_discuss_turn_end"

    def get_phase(self) -> GamePhase:
        return GamePhase.DAY_DISCUSS

    def on_enter(self):
        alive_ids = [player.id for player in self.game.players if player.is_alive]
        speaking_order = self.gm.judge_system.determine_speaking_order(
            alive_ids, self.game.sheriff_id
        )
        self.prime_speaking_window(speaking_order, participant_ids=alive_ids)
        order_str = ", ".join(f"{player_id}号" for player_id in speaking_order)
        self.add_log(
            f"现在开始自由讨论。发言顺序：{order_str}",
            data=self.build_event_data(
                "day_discuss_started",
                speaking_order=speaking_order,
                current_speaker_id=self.current_speaker_id(),
                sheriff_id=self.game.sheriff_id,
            ),
        )

    def _is_eligible_speaker(self, player: Player) -> bool:
        return player.is_alive

    def _speech_content(self, player: Player, action: ActionRequest) -> str:
        return f"{player.id}号: {action.content}"

    def _turn_end_content(self, player: Player) -> str:
        return f"{player.id}号结束发言。"

    def _on_window_finished(self) -> GamePhase:
        return GamePhase.DAY_VOTE
