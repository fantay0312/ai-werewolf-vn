from app.core.phase_handler import PhaseHandler
from app.models.game_state import GamePhase, ActionType
from app.models.action_model import ActionRequest


class DayLastWordsHandler(PhaseHandler):
    def get_phase(self) -> GamePhase:
        return GamePhase.DAY_LAST_WORDS

    def on_enter(self):
        self.eligible_speakers = sorted(self.game.dead_players)
        next_phase = self._get_next_phase()

        if not self.eligible_speakers:
            self.game.speaking_order = []
            return

        self.prime_speaking_window(self.eligible_speakers, participant_ids=self.eligible_speakers)

        speaker_str = ", ".join([f"{pid}号" for pid in self.eligible_speakers])
        self.add_log(
            f"请发表遗言。发言顺序：{speaker_str}",
            data=self.build_event_data(
                "day_last_words_started",
                eligible_speaker_ids=list(self.eligible_speakers),
                speaking_order=list(self.game.speaking_order),
                current_speaker_id=self.current_speaker_id(),
                next_phase_hint=next_phase.value,
            ),
        )

    def process_action(self, action: ActionRequest) -> bool:
        if not self.is_current_speaker(action.player_id):
            return False

        player = self.find_player(action.player_id)
        if not player:
            return False

        speaker_index = self.game.current_speaker_index

        if action.type == ActionType.SPEECH:
            player.has_acted = True
            self.advance_speaker()
            next_speaker = self.activate_current_speaker()
            self.add_log(
                f"{player.id}号(遗言): {action.content}",
                player_id=player.id,
                log_type="speech",
                data=self.build_event_data(
                    "day_last_words_speech",
                    action="speech",
                    speaker_id=player.id,
                    speaker_index=speaker_index,
                    speaking_order=list(self.game.speaking_order),
                    next_speaker_id=next_speaker.id if next_speaker else None,
                    next_phase_hint=self._get_next_phase().value,
                ),
            )
            return True

        if action.type in (ActionType.CONFIRM, ActionType.PASS):
            player.has_acted = True
            self.advance_speaker()
            next_speaker = self.activate_current_speaker()
            self.add_log(
                f"{player.id}号结束遗言。",
                player_id=player.id,
                log_type="action",
                data=self.build_event_data(
                    "day_last_words_turn_end",
                    action=action.type.value,
                    speaker_id=player.id,
                    speaker_index=speaker_index,
                    speaking_order=list(self.game.speaking_order),
                    next_speaker_id=next_speaker.id if next_speaker else None,
                    next_phase_hint=self._get_next_phase().value,
                ),
            )
            return True

        return False

    def try_advance(self) -> GamePhase:
        if self.all_speakers_done():
            next_phase = self._get_next_phase()
            if next_phase == GamePhase.SHERIFF_ELECTION:
                self.game.pending_sheriff_election = False
            return next_phase
        return None

    def _get_next_phase(self) -> GamePhase:
        if self.game.pending_sheriff_election and not self.game.election_cancelled:
            return GamePhase.SHERIFF_ELECTION
        return GamePhase.DAY_DISCUSS
