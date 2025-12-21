from typing import Dict, List, Optional
from collections import Counter
from app.core.phase_handler import PhaseHandler
from app.models.game_state import GamePhase, ActionType, GameLog, Role
from app.models.action_model import ActionRequest
from app.core.rules import Rules
import uuid

class DayVoteHandler(PhaseHandler):
    def get_phase(self) -> GamePhase:
        return GamePhase.DAY_VOTE

    def on_enter(self):
        log = GameLog(
            id=str(uuid.uuid4()),
            day=self.game.day,
            phase=self.game.phase,
            content="请投票放逐一名玩家。",
            is_public=True
        )
        self.game.game_logs.append(log)
        
        self.game.votes = {}
        for p in self.game.players:
            if p.is_alive:
                p.has_acted = False

    def process_action(self, action: ActionRequest) -> bool:
        player = next((p for p in self.game.players if p.id == action.player_id), None)
        if not player or not player.is_alive:
            return False

        if action.type == ActionType.VOTE:
            try:
                target_id = 0 if action.target_id is None else int(action.target_id)
            except (ValueError, TypeError):
                return False
            self.game.votes[player.id] = target_id

            player.has_acted = True
            return True

        return False

    def try_advance(self) -> GamePhase:
        alive_players = [p for p in self.game.players if p.is_alive]
        
        if all(p.has_acted for p in alive_players):
            return GamePhase.DAY_VOTE_RESULT
            
        return None