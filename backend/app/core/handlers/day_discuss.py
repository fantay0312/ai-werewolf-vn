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
        self.prime_speaking_window(speaking_order, participant_ids=alive_ids)

        order_str = ", ".join([f"{pid}号" for pid in speaking_order])
        self.add_log(
            f"现在开始自由讨论。发言顺序：{order_str}",
            data=self.build_event_data(
                "day_discuss_started",
                speaking_order=speaking_order,
                current_speaker_id=self.current_speaker_id(),
                sheriff_id=self.game.sheriff_id,
            ),
        )

    def process_action(self, action: ActionRequest) -> bool:
        player = self.find_alive_player(action.player_id)
        if not player or not self.is_current_speaker(action.player_id):
            return False

        speaker_index = self.game.current_speaker_index

        if action.type == ActionType.SPEECH:
            player.has_acted = True
            self.advance_speaker()
            next_speaker = self.activate_current_speaker()

            self.add_log(
                f"{player.id}号: {action.content}",
                player_id=player.id,
                log_type="speech",
                data=self.build_event_data(
                    "day_discuss_speech",
                    action="speech",
                    speaker_id=player.id,
                    speaker_index=speaker_index,
                    speaking_order=list(self.game.speaking_order),
                    next_speaker_id=next_speaker.id if next_speaker else None,
                ),
            )
            return True

        if action.type in (ActionType.CONFIRM, ActionType.PASS):
            player.has_acted = True
            self.advance_speaker()
            next_speaker = self.activate_current_speaker()
            self.add_log(
                f"{player.id}号结束发言。",
                player_id=player.id,
                log_type="action",
                data=self.build_event_data(
                    "day_discuss_turn_end",
                    action=action.type.value,
                    speaker_id=player.id,
                    speaker_index=speaker_index,
                    speaking_order=list(self.game.speaking_order),
                    next_speaker_id=next_speaker.id if next_speaker else None,
                ),
            )
            return True

        return False

    def try_advance(self) -> GamePhase:
        if self.all_speakers_done():
            return GamePhase.DAY_VOTE
        return None
