from typing import Dict, List, Optional
from collections import Counter
from app.core.phase_handler import PhaseHandler
from app.models.game_state import GamePhase, ActionType, GameLog, Role
from app.models.action_model import ActionRequest
import uuid

class NightWolfVoteHandler(PhaseHandler):
    def get_phase(self) -> GamePhase:
        return GamePhase.NIGHT_WOLF_VOTE

    def on_enter(self):
        log = GameLog(
            id=str(uuid.uuid4()),
            day=self.game.day,
            phase=self.game.phase,
            content="狼人请执行击杀目标。",
            is_public=False
        )
        self.game.game_logs.append(log)
        
        # Reset votes and action status
        self.game.votes = {}
        for p in self.game.players:
            if p.role in [Role.WOLF, Role.WOLF_KING] and p.is_alive:
                p.has_acted = False

    def process_action(self, action: ActionRequest) -> bool:
        player = next((p for p in self.game.players if p.id == action.player_id), None)
        if not player or player.role not in [Role.WOLF, Role.WOLF_KING]:
            return False

        if action.type == ActionType.KILL:
            if action.target_id is None:
                return False
            
            # Record vote
            self.game.votes[player.id] = action.target_id
            player.has_acted = True
            
            log = GameLog(
                id=str(uuid.uuid4()),
                day=self.game.day,
                phase=self.game.phase,
                content=f"{player.id}号 选择了击杀 {action.target_id}号",
                player_id=player.id,
                is_public=False
            )
            self.game.game_logs.append(log)
            return True
            
        return False

    def try_advance(self) -> GamePhase:
        alive_wolves = [p for p in self.game.players if p.role in [Role.WOLF, Role.WOLF_KING] and p.is_alive]
        
        # Wait for all wolves to vote
        if all(p.has_acted for p in alive_wolves):
            # Tally votes
            vote_counts = Counter(self.game.votes.values())
            if not vote_counts:
                # No votes (shouldn't happen if all acted), default to no kill
                self.game.wolf_kill_target = None
            else:
                # Find target with max votes
                # Tie-breaker: Random or first? For now, simple max.
                target_id, count = vote_counts.most_common(1)[0]
                
                # Check for tie
                max_votes = count
                candidates = [pid for pid, c in vote_counts.items() if c == max_votes]
                
                if len(candidates) > 1:
                    # Tie: Wolf King decides? Or random? 
                    # Simplified: First candidate wins (or could trigger re-vote)
                    # For MVP, just pick the first one.
                    self.game.wolf_kill_target = candidates[0]
                else:
                    self.game.wolf_kill_target = target_id
            
            # Mark the target as killed (but not dead yet, waiting for witch/guard)
            if self.game.wolf_kill_target:
                target = next((p for p in self.game.players if p.id == self.game.wolf_kill_target), None)
                if target:
                    target.killed_by_wolf = True

            return GamePhase.NIGHT_SEER
            
        return None