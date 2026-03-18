from app.core.phase_handler import PhaseHandler
from app.models.game_state import GamePhase, ActionType
from app.models.action_model import ActionRequest


class DayLastWordsHandler(PhaseHandler):
    def get_phase(self) -> GamePhase:
        return GamePhase.DAY_LAST_WORDS

    def on_enter(self):
        self.eligible_speakers = self.game.dead_players

        if not self.eligible_speakers:
            self.game.speaking_order = []
            return

        self.eligible_speakers.sort()
        self.game.speaking_order = self.eligible_speakers
        self.game.current_speaker_index = 0

        for pid in self.eligible_speakers:
            player = self.find_player(pid)
            if player:
                player.has_acted = False

        speaker_str = ", ".join([f"{pid}号" for pid in self.eligible_speakers])
        self.add_log(f"请发表遗言。发言顺序：{speaker_str}")

    def process_action(self, action: ActionRequest) -> bool:
        if not self.is_current_speaker(action.player_id):
            return False

        player = self.find_player(action.player_id)
        if not player:
            return False

        if action.type == ActionType.SPEECH:
            self.add_log(
                f"{player.id}号(遗言): {action.content}",
                player_id=player.id,
                log_type="speech",
            )
            player.has_acted = True
            self.advance_speaker()
            return True

        if action.type in (ActionType.CONFIRM, ActionType.PASS):
            player.has_acted = True
            self.advance_speaker()
            return True

        return False

    def try_advance(self) -> GamePhase:
        if self.all_speakers_done():
            return GamePhase.SHERIFF_ELECTION
        return None
