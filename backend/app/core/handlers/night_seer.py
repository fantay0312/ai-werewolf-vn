from app.core.phase_handler import PhaseHandler
from app.models.game_state import GamePhase, ActionType, GameLog, Role
from app.models.action_model import ActionRequest
import uuid

class NightSeerHandler(PhaseHandler):
    def get_phase(self) -> GamePhase:
        return GamePhase.NIGHT_SEER

    def on_enter(self):
        log = GameLog(
            id=str(uuid.uuid4()),
            day=self.game.day,
            phase=self.game.phase,
            content="预言家请查验身份。",
            is_public=False
        )
        self.game.game_logs.append(log)
        
        for p in self.game.players:
            if p.role == Role.SEER:
                p.has_acted = False

    def process_action(self, action: ActionRequest) -> bool:
        player = next((p for p in self.game.players if p.id == action.player_id), None)
        if not player or player.role != Role.SEER:
            return False

        if action.type == ActionType.CHECK:
            if action.target_id is None:
                return False
                
            target = next((p for p in self.game.players if p.id == action.target_id), None)
            if not target:
                return False
            
            # 检查目标是否存活
            if not target.is_alive:
                return False
                
            # Perform check
            is_good = target.role not in [Role.WOLF, Role.WOLF_KING]
            result_text = "好人" if is_good else "狼人"
            
            # Log result privately to Seer
            log = GameLog(
                id=str(uuid.uuid4()),
                day=self.game.day,
                phase=self.game.phase,
                content=f"查验结果：{target.id}号是 {result_text}",
                player_id=player.id,
                is_public=False,
                data={
                    "action": "seer_check",
                    "target_id": target.id,
                    "result": "good" if is_good else "bad"
                }
            )
            self.game.game_logs.append(log)
            
            # 标记目标被查验过（用于后续逻辑，如防止重复查验等）
            target.checked_by_seer = True
            player.has_acted = True
            return True
            
        elif action.type == ActionType.PASS:
            player.has_acted = True
            return True
            
        return False

    def try_advance(self) -> GamePhase:
        seer = next((p for p in self.game.players if p.role == Role.SEER), None)
        
        # If Seer is dead, auto-advance (or maybe wait a random delay to simulate?)
        if not seer or not seer.is_alive:
            return GamePhase.NIGHT_WITCH
            
        # If Seer has acted
        if seer.has_acted:
            return GamePhase.NIGHT_WITCH
            
        return None