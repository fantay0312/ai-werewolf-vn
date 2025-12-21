from app.core.phase_handler import PhaseHandler
from app.models.game_state import GamePhase, ActionType, GameLog, Role
from app.models.action_model import ActionRequest
import uuid

class DayDiscussHandler(PhaseHandler):
    def get_phase(self) -> GamePhase:
        return GamePhase.DAY_DISCUSS

    def on_enter(self):
        # Determine speaking order
        alive_ids = [p.id for p in self.game.players if p.is_alive]
        sheriff_id = self.game.sheriff_id
        
        speaking_order = self.gm.judge_system.determine_speaking_order(alive_ids, sheriff_id)
        self.game.speaking_order = speaking_order
        self.game.current_speaker_index = 0
        
        # Broadcast speaking order
        order_str = ", ".join([f"{pid}号" for pid in speaking_order])
        content = f"现在开始自由讨论。发言顺序：{order_str}"
        
        log = GameLog(
            id=str(uuid.uuid4()),
            day=self.game.day,
            phase=self.game.phase,
            content=content,
            is_public=True
        )
        self.game.game_logs.append(log)
        
        for p in self.game.players:
            if p.is_alive:
                p.has_acted = False

    def process_action(self, action: ActionRequest) -> bool:
        player = next((p for p in self.game.players if p.id == action.player_id), None)
        if not player or not player.is_alive:
            return False

        if action.type == ActionType.SPEECH:
            log = GameLog(
                id=str(uuid.uuid4()),
                day=self.game.day,
                phase=self.game.phase,
                content=f"{player.id}号: {action.content}",
                player_id=player.id,
                is_public=True
            )
            self.game.game_logs.append(log)
            player.has_acted = True
            return True
            
        elif action.type in [ActionType.CONFIRM, ActionType.PASS]:
            # Player chooses to end their turn/discussion (both confirm and pass are valid)
            player.has_acted = True
            return True

        return False

    def try_advance(self) -> GamePhase:
        # If all alive players have acted (spoken or confirmed), move to vote
        alive_players = [p for p in self.game.players if p.is_alive]
        if all(p.has_acted for p in alive_players):
            return GamePhase.DAY_VOTE
        return None