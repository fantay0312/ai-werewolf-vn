from app.core.phase_handler import PhaseHandler
from app.models.game_state import GamePhase, ActionType, GameLog, Role, WolfDiscussMessage
from app.models.action_model import ActionRequest
import uuid

class NightWolfDiscussHandler(PhaseHandler):
    def get_phase(self) -> GamePhase:
        return GamePhase.NIGHT_WOLF_DISCUSS

    def on_enter(self):
        # Initialize or increment discussion round
        if not hasattr(self.game, 'wolf_discuss_round'):
            self.game.wolf_discuss_round = 1
        else:
            self.game.wolf_discuss_round += 1
            
        # Announce discussion round
        log = GameLog(
            id=str(uuid.uuid4()),
            day=self.game.day,
            phase=self.game.phase,
            content=f"狼人讨论第 {self.game.wolf_discuss_round}/3 轮开始。",
            is_public=False # Only visible to wolves (frontend needs to filter)
        )
        self.game.game_logs.append(log)
        
        # Reset action status for wolves
        for p in self.game.players:
            if p.role in [Role.WOLF, Role.WOLF_KING] and p.is_alive:
                p.has_acted = False

    def process_action(self, action: ActionRequest) -> bool:
        player = next((p for p in self.game.players if p.id == action.player_id), None)
        if not player:
            return False
            
        # Only wolves can act
        if player.role not in [Role.WOLF, Role.WOLF_KING]:
            return False

        if action.type == ActionType.SPEECH:
            # Log the speech (private to wolves)
            log = GameLog(
                id=str(uuid.uuid4()),
                day=self.game.day,
                phase=self.game.phase,
                content=f"{player.id}号(狼人): {action.content}",
                player_id=player.id,
                is_public=False,
                type="speech"
            )
            self.game.game_logs.append(log)

            # Add to wolf discuss messages for frontend display
            msg = WolfDiscussMessage(
                id=str(uuid.uuid4()),
                speaker_id=player.id,
                content=action.content,
                round=self.game.wolf_discuss_round
            )
            self.game.wolf_discuss_messages.append(msg)

            player.has_acted = True
            return True
            
        elif action.type == ActionType.PASS:
            # Wolf chooses to skip speech
            player.has_acted = True
            return True
            
        return False

    def try_advance(self) -> GamePhase:
        # Check if all alive wolves have acted
        alive_wolves = [p for p in self.game.players if p.role in [Role.WOLF, Role.WOLF_KING] and p.is_alive]
        if all(p.has_acted for p in alive_wolves):
            if self.game.wolf_discuss_round < 3:
                # Continue to next round of discussion (re-enter same phase)
                # Note: GameManager logic needs to handle re-entry if phase is same
                # For now, we assume GameManager resets has_acted on re-entry
                return GamePhase.NIGHT_WOLF_DISCUSS
            else:
                # Done with discussion, move to vote
                delattr(self.game, 'wolf_discuss_round') # Cleanup
                return GamePhase.NIGHT_WOLF_VOTE
        return None