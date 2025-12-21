from app.core.phase_handler import PhaseHandler
from app.models.game_state import GamePhase, ActionType, GameLog, Role
from app.models.action_model import ActionRequest
import uuid

class SheriffTransferHandler(PhaseHandler):
    def get_phase(self) -> GamePhase:
        return GamePhase.SHERIFF_TRANSFER

    def on_enter(self):
        sheriff = next((p for p in self.game.players if p.is_sheriff), None)
        if sheriff and not sheriff.is_alive:
            log = GameLog(
                id=str(uuid.uuid4()),
                day=self.game.day,
                phase=self.game.phase,
                content=f"{sheriff.id}号玩家(警长)死亡，请移交警徽。",
                is_public=True
            )
            self.game.game_logs.append(log)
            sheriff.has_acted = False
        else:
            # Sheriff is alive or no sheriff, skip
            pass

    def process_action(self, action: ActionRequest) -> bool:
        player = next((p for p in self.game.players if p.id == action.player_id), None)
        if not player or not player.is_sheriff:
            return False

        if action.type == ActionType.VOTE: # Reuse VOTE for transfer? Or create TRANSFER action?
            # Let's use VOTE with target_id for transfer, or target_id=0 for tear?
            # Or better, use specific types if we can.
            # Let's use VOTE for simplicity in frontend, or add TRANSFER type.
            # We added ActionType.VOTE. Let's assume VOTE target_id is the new sheriff.
            
            target_id = action.target_id
            if target_id == 0 or target_id is None:
                # Tear badge
                self.game.sheriff_id = None
                player.is_sheriff = False
                
                log = GameLog(
                    id=str(uuid.uuid4()),
                    day=self.game.day,
                    phase=self.game.phase,
                    content=f"{player.id}号撕掉了警徽。",
                    is_public=True
                )
                self.game.game_logs.append(log)
            else:
                # Transfer
                target = next((p for p in self.game.players if p.id == target_id), None)
                if not target or not target.is_alive:
                    return False
                    
                player.is_sheriff = False
                target.is_sheriff = True
                self.game.sheriff_id = target.id
                
                log = GameLog(
                    id=str(uuid.uuid4()),
                    day=self.game.day,
                    phase=self.game.phase,
                    content=f"{player.id}号将警徽移交给了{target.id}号。",
                    is_public=True
                )
                self.game.game_logs.append(log)
                
            player.has_acted = True
            return True
            
        return False

    def try_advance(self) -> GamePhase:
        # Check if sheriff is dead and handled transfer
        sheriff = next((p for p in self.game.players if p.is_sheriff), None)
        
        # If current sheriff is alive, we are done
        if sheriff and sheriff.is_alive:
            return self._get_next_phase()
            
        # If no sheriff (torn), done
        if not sheriff:
            return self._get_next_phase()
            
        # If sheriff is dead and hasn't acted
        if not sheriff.has_acted:
            return None
            
        return self._get_next_phase()

    def _get_next_phase(self):
        if hasattr(self.game, 'next_phase_after_skill') and self.game.next_phase_after_skill:
            return self.game.next_phase_after_skill
        return GamePhase.DAY_DISCUSS