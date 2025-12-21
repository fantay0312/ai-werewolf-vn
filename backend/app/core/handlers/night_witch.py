from app.core.phase_handler import PhaseHandler
from app.models.game_state import GamePhase, ActionType, GameLog, Role
from app.models.action_model import ActionRequest
import uuid

class NightWitchHandler(PhaseHandler):
    def get_phase(self) -> GamePhase:
        return GamePhase.NIGHT_WITCH

    def on_enter(self):
        # Notify Witch about who died (if they have antidote)
        witch = next((p for p in self.game.players if p.role == Role.WITCH), None)
        content = "女巫请行动。"
        
        if witch and witch.is_alive and not witch.antidote_used:
            killed_id = self.game.wolf_kill_target
            if killed_id:
                content += f" 今晚 {killed_id} 号被杀了。"
            else:
                content += " 今晚平安夜。"
        
        log = GameLog(
            id=str(uuid.uuid4()),
            day=self.game.day,
            phase=self.game.phase,
            content=content,
            player_id=witch.id if witch else None,
            is_public=False
        )
        self.game.game_logs.append(log)
        
        if witch:
            witch.has_acted = False

    def process_action(self, action: ActionRequest) -> bool:
        player = next((p for p in self.game.players if p.id == action.player_id), None)
        if not player or player.role != Role.WITCH:
            return False

        if action.type == ActionType.SAVE:
            if player.antidote_used:
                return False
            
            # Save the person killed by wolves
            target_id = self.game.wolf_kill_target
            if target_id:
                target = next((p for p in self.game.players if p.id == target_id), None)
                if target:
                    target.saved_by_witch = True
                    player.antidote_used = True
                    player.has_acted = True
                    
                    # Log action
                    log = GameLog(
                        id=str(uuid.uuid4()),
                        day=self.game.day,
                        phase=self.game.phase,
                        content=f"女巫使用解药救了 {target.id} 号",
                        player_id=player.id,
                        is_public=False,
                        data={
                            "action": "witch_save",
                            "target_id": target.id
                        }
                    )
                    self.game.game_logs.append(log)
                    return True
            return False

        elif action.type == ActionType.POISON:
            if player.poison_used or action.target_id is None:
                return False
                
            target = next((p for p in self.game.players if p.id == action.target_id), None)
            if target:
                target.poisoned_by_witch = True
                player.poison_used = True
                player.has_acted = True
                
                # Log action
                log = GameLog(
                    id=str(uuid.uuid4()),
                    day=self.game.day,
                    phase=self.game.phase,
                    content=f"女巫使用毒药毒了 {target.id} 号",
                    player_id=player.id,
                    is_public=False,
                    data={
                        "action": "witch_poison",
                        "target_id": target.id
                    }
                )
                self.game.game_logs.append(log)
                return True
            return False
            
        elif action.type == ActionType.PASS:
            player.has_acted = True
            return True
            
        return False

    def try_advance(self) -> GamePhase:
        witch = next((p for p in self.game.players if p.role == Role.WITCH), None)
        
        if not witch or not witch.is_alive:
            return GamePhase.NIGHT_GUARD
            
        if witch.has_acted:
            return GamePhase.NIGHT_GUARD
            
        return None