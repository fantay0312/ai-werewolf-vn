from app.core.phase_handler import PhaseHandler
from app.models.game_state import GamePhase, ActionType, GameLog, Role
from app.models.action_model import ActionRequest
import uuid

class NightGuardHandler(PhaseHandler):
    def get_phase(self) -> GamePhase:
        return GamePhase.NIGHT_GUARD

    def on_enter(self):
        log = GameLog(
            id=str(uuid.uuid4()),
            day=self.game.day,
            phase=self.game.phase,
            content="守卫请守护。",
            is_public=False
        )
        self.game.game_logs.append(log)
        
        for p in self.game.players:
            if p.role == Role.GUARD:
                p.has_acted = False

    def process_action(self, action: ActionRequest) -> bool:
        player = next((p for p in self.game.players if p.id == action.player_id), None)
        if not player or player.role != Role.GUARD:
            return False

        if action.type == ActionType.GUARD:
            if action.target_id is None:
                return False
                
            # Cannot guard same person twice
            if self.game.last_guarded_player == action.target_id:
                return False
                
            target = next((p for p in self.game.players if p.id == action.target_id), None)
            if target:
                target.protected_by_guard = True
                self.game.last_guarded_player = action.target_id
                player.has_acted = True
                
                # Log action
                log = GameLog(
                    id=str(uuid.uuid4()),
                    day=self.game.day,
                    phase=self.game.phase,
                    content=f"守卫守护了 {target.id} 号",
                    player_id=player.id,
                    is_public=False,
                    data={
                        "action": "guard_protect",
                        "target_id": target.id
                    }
                )
                self.game.game_logs.append(log)
                return True
            return False
            
        elif action.type == ActionType.PASS:
            player.has_acted = True
            self.game.last_guarded_player = None # Reset if passed? Usually pass means no guard, so next turn can guard anyone.
            return True
            
        return False

    def try_advance(self) -> GamePhase:
        guard = next((p for p in self.game.players if p.role == Role.GUARD), None)
        
        if not guard or not guard.is_alive:
            return GamePhase.NIGHT_RESOLVE
            
        if guard.has_acted:
            return GamePhase.NIGHT_RESOLVE
            
        return None