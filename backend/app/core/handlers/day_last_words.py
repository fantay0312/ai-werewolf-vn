from app.core.handlers.turn_window import TurnWindowHandler
from app.models.action_model import ActionRequest
from app.models.game_state import GamePhase, Player


class DayLastWordsHandler(TurnWindowHandler):
    speech_event = "day_last_words_speech"
    turn_end_event = "day_last_words_turn_end"

    def get_phase(self) -> GamePhase:
        return GamePhase.DAY_LAST_WORDS

    def on_enter(self):
        eligible_speakers = sorted(self.game.dead_players)
        next_phase = self._get_next_phase()
        if not eligible_speakers:
            self.game.speaking_order = []
            return
        self.prime_speaking_window(eligible_speakers, eligible_speakers)
        speaker_str = ", ".join(f"{player_id}号" for player_id in eligible_speakers)
        self.add_log(
            f"请发表遗言。发言顺序：{speaker_str}",
            data=self.build_event_data(
                "day_last_words_started",
                eligible_speaker_ids=list(eligible_speakers),
                speaking_order=list(self.game.speaking_order),
                current_speaker_id=self.current_speaker_id(),
                next_phase_hint=next_phase.value,
            ),
        )

    def _is_eligible_speaker(self, player: Player) -> bool:
        return player.id in self.game.dead_players and player.id in self.game.speaking_order

    def _speech_content(self, player: Player, action: ActionRequest) -> str:
        return f"{player.id}号(遗言): {action.content}"

    def _turn_end_content(self, player: Player) -> str:
        return f"{player.id}号结束遗言。"

    def _turn_event_fields(self) -> dict:
        return {
            "speaking_order": list(self.game.speaking_order),
            "next_phase_hint": self._get_next_phase().value,
        }

    def _on_window_finished(self) -> GamePhase:
        next_phase = self._get_next_phase()
        if next_phase == GamePhase.SHERIFF_ELECTION:
            self.game.pending_sheriff_election = False
        return next_phase

    def _get_next_phase(self) -> GamePhase:
        if self.game.pending_sheriff_election and not self.game.election_cancelled:
            return GamePhase.SHERIFF_ELECTION
        return GamePhase.DAY_DISCUSS
