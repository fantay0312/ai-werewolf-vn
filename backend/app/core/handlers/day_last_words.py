from app.core.phase_handler import PhaseHandler
from app.models.game_state import GamePhase, ActionType, GameLog
from app.models.action_model import ActionRequest
import uuid

class DayLastWordsHandler(PhaseHandler):
    def get_phase(self) -> GamePhase:
        return GamePhase.DAY_LAST_WORDS

    def on_enter(self):
        # Identify players eligible for last words
        # In this phase (triggered from DayStart), it's Night 1 deaths
        self.eligible_speakers = self.game.dead_players
        
        if not self.eligible_speakers:
            # Should not happen if logic is correct, but handle gracefully
            self.game.speaking_order = []
            return

        # Sort by ID for order
        self.eligible_speakers.sort()
        self.game.speaking_order = self.eligible_speakers
        self.game.current_speaker_index = 0
        
        # Reset acted status for eligible speakers
        for pid in self.eligible_speakers:
            player = next((p for p in self.game.players if p.id == pid), None)
            if player:
                player.has_acted = False

        # Broadcast
        speaker_str = ", ".join([f"{pid}号" for pid in self.eligible_speakers])
        content = f"请发表遗言。发言顺序：{speaker_str}"
        
        log = GameLog(
            id=str(uuid.uuid4()),
            day=self.game.day,
            phase=self.game.phase,
            content=content,
            is_public=True
        )
        self.game.game_logs.append(log)

    def process_action(self, action: ActionRequest) -> bool:
        # Check if it's the current speaker's turn
        if not self.game.speaking_order:
            return False
            
        current_speaker_id = self.game.speaking_order[self.game.current_speaker_index]
        if action.player_id != current_speaker_id:
            return False
            
        player = next((p for p in self.game.players if p.id == action.player_id), None)
        if not player:
            return False

        if action.type == ActionType.SPEECH:
            log = GameLog(
                id=str(uuid.uuid4()),
                day=self.game.day,
                phase=self.game.phase,
                content=f"{player.id}号(遗言): {action.content}",
                player_id=player.id,
                is_public=True,
                type="speech" # Mark as speech for frontend
            )
            self.game.game_logs.append(log)
            player.has_acted = True
            
            # Move to next speaker
            self._advance_speaker()
            return True
            
        elif action.type in [ActionType.CONFIRM, ActionType.PASS]:
            # End speech (both confirm and pass are valid)
            player.has_acted = True
            self._advance_speaker()
            return True

        return False

    def _advance_speaker(self):
        self.game.current_speaker_index += 1

    def try_advance(self) -> GamePhase:
        # If all speakers have finished
        if self.game.current_speaker_index >= len(self.game.speaking_order):
            # After last words (Night 1), go to Sheriff Election
            return GamePhase.SHERIFF_ELECTION
            
        return None
