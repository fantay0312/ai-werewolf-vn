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
        )

        self.game.speaking_order = pk_candidates
        self.game.current_speaker_index = 0

        for pid in pk_candidates:
            player = self.find_player(pid)
            if player:
                player.has_acted = False

    def process_action(self, action: ActionRequest) -> bool:
        if not self.is_current_speaker(action.player_id):
            return False

        player = self.find_player(action.player_id)
        if not player:
            return False

        if action.type == ActionType.SPEECH:
            self.add_log(
                f"{player.id}号(PK发言): {action.content}",
                player_id=player.id,
                log_type="speech",
            )
            player.has_acted = True
            self.advance_speaker()
            return True

        if action.type == ActionType.CONFIRM:
            player.has_acted = True
            self.advance_speaker()
            return True

        return False

    def try_advance(self) -> GamePhase:
        if self.all_speakers_done():
            return GamePhase.DAY_PK_VOTE
        return None
