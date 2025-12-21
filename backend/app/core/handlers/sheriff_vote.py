from app.core.phase_handler import PhaseHandler
from app.models.game_state import GamePhase, ActionType, GameLog, Role
from app.models.action_model import ActionRequest
import uuid

class SheriffVoteHandler(PhaseHandler):
    def get_phase(self) -> GamePhase:
        return GamePhase.SHERIFF_VOTE

    def on_enter(self):
        candidates = sorted(self.game.sheriff_candidate_ids)
        candidates_str = ", ".join([f"{pid}号" for pid in candidates])
        
        log = GameLog(
            id=str(uuid.uuid4()),
            day=self.game.day,
            phase=self.game.phase,
            content=f"请未竞选的玩家在 {candidates_str} 中投票选出警长。",
            is_public=True
        )
        self.game.game_logs.append(log)
        
        self.game.votes = {}
        
        # Candidates cannot vote
        for p in self.game.players:
            if p.is_alive:
                if p.id in self.game.sheriff_candidate_ids:
                    p.has_acted = True # Skip candidates
                else:
                    p.has_acted = False

    def process_action(self, action: ActionRequest) -> bool:
        player = next((p for p in self.game.players if p.id == action.player_id), None)
        if not player or not player.is_alive:
            return False
            
        # Double check: Candidates cannot vote
        if player.id in self.game.sheriff_candidate_ids:
            return False

        if action.type == ActionType.VOTE:
            if action.target_id is None:
                self.game.votes[player.id] = 0 # Abstain
            elif action.target_id in self.game.sheriff_candidate_ids:
                self.game.votes[player.id] = action.target_id
            else:
                return False # Invalid target (must be a candidate)
                
            player.has_acted = True
            return True
            
        return False

    def try_advance(self) -> GamePhase:
        # Check if all eligible voters have acted
        eligible_voters = [p for p in self.game.players if p.is_alive and p.id not in self.game.sheriff_candidate_ids]
        if all(p.has_acted for p in eligible_voters):
            # Calculate result immediately here or in a separate Result phase?
            # Let's do it here to keep it simple, or create a Result phase if we want PK (PK omitted for MVP)
            
            # Tally votes
            from collections import Counter
            vote_counts = Counter([t for t in self.game.votes.values() if t != 0])
            
            # Log votes
            content = "警长投票结果：\n"
            for voter_id, target_id in self.game.votes.items():
                target_name = f"{target_id}号" if target_id != 0 else "弃票"
                content += f"{voter_id}号 -> {target_name}\n"
            
            log = GameLog(
                id=str(uuid.uuid4()),
                day=self.game.day,
                phase=self.game.phase,
                content=content,
                is_public=True
            )
            self.game.game_logs.append(log)
            
            if vote_counts:
                target_id, count = vote_counts.most_common(1)[0]
                # Check tie
                max_votes = count
                winners = [pid for pid, c in vote_counts.items() if c == max_votes]
                
                if len(winners) == 1:
                    sheriff_id = winners[0]
                    self.game.sheriff_id = sheriff_id
                    sheriff = next(p for p in self.game.players if p.id == sheriff_id)
                    sheriff.is_sheriff = True
                    
                    log = GameLog(
                        id=str(uuid.uuid4()),
                        day=self.game.day,
                        phase=self.game.phase,
                        content=f"{sheriff_id}号当选警长！",
                        is_public=True
                    )
                    self.game.game_logs.append(log)
                else:
                    log = GameLog(
                        id=str(uuid.uuid4()),
                        day=self.game.day,
                        phase=self.game.phase,
                        content="平票，本局无警长。",
                        is_public=True
                    )
                    self.game.game_logs.append(log)
            else:
                log = GameLog(
                    id=str(uuid.uuid4()),
                    day=self.game.day,
                    phase=self.game.phase,
                    content="无人投票，本局无警长。",
                    is_public=True
                )
                self.game.game_logs.append(log)
                
            return GamePhase.NIGHT_START

        return None