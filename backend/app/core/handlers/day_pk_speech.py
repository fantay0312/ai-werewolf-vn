"""平票PK发言阶段处理器"""
from app.core.phase_handler import PhaseHandler
from app.models.game_state import GamePhase, ActionType
from app.models.action_model import ActionRequest


class DayPKSpeechHandler(PhaseHandler):
    def get_phase(self) -> GamePhase:
        return GamePhase.DAY_PK_SPEECH

    def on_enter(self):
        pk_candidates = sorted(self.game.pk_candidates)
        if not pk_candidates:
            return

        candidates_str = ", ".join([f"{pid}号" for pid in pk_candidates])
        self.add_log(
            f"进入平票PK环节。PK玩家：{candidates_str}。请依次发表PK发言。",
            log_type="broadcast",
            data=self.build_event_data(
                "day_pk_speech_started",
                pk_candidate_ids=list(pk_candidates),
                pk_round=self.game.pk_round,
                speaking_order=list(pk_candidates),
                current_speaker_id=pk_candidates[0],
                next_phase_hint=GamePhase.DAY_PK_VOTE.value,
            ),
        )

        self.prime_speaking_window(pk_candidates, participant_ids=pk_candidates)

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
                f"{player.id}号(PK发言): {action.content}",
                player_id=player.id,
                log_type="speech",
                data=self.build_event_data(
                    "day_pk_speech",
                    action="speech",
                    speaker_id=player.id,
                    speaker_index=speaker_index,
                    pk_candidate_ids=list(self.game.pk_candidates),
                    speaking_order=list(self.game.speaking_order),
                    next_speaker_id=next_speaker.id if next_speaker else None,
                    next_phase_hint=GamePhase.DAY_PK_VOTE.value,
                ),
            )
            return True

        if action.type in (ActionType.CONFIRM, ActionType.PASS):
            player.has_acted = True
            self.advance_speaker()
            next_speaker = self.activate_current_speaker()
            self.add_log(
                f"{player.id}号结束PK发言。",
                player_id=player.id,
                log_type="action",
                data=self.build_event_data(
                    "day_pk_speech_turn_end",
                    action=action.type.value,
                    speaker_id=player.id,
                    speaker_index=speaker_index,
                    pk_candidate_ids=list(self.game.pk_candidates),
                    speaking_order=list(self.game.speaking_order),
                    next_speaker_id=next_speaker.id if next_speaker else None,
                    next_phase_hint=GamePhase.DAY_PK_VOTE.value,
                ),
            )
            return True

        return False

    def try_advance(self) -> GamePhase:
        if self.all_speakers_done():
            return GamePhase.DAY_PK_VOTE
        return None
