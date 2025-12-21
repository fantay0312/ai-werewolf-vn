from app.core.phase_handler import PhaseHandler
from app.models.game_state import GamePhase, ActionType, GameLog, Role
from app.models.action_model import ActionRequest
import uuid

class SheriffSpeechHandler(PhaseHandler):
    def get_phase(self) -> GamePhase:
        return GamePhase.SHERIFF_SPEECH

    def on_enter(self):
        candidates = sorted(self.game.sheriff_candidate_ids)
        candidates_str = ", ".join([f"{pid}号" for pid in candidates])
        
        log = GameLog(
            id=str(uuid.uuid4()),
            day=self.game.day,
            phase=self.game.phase,
            content=f"竞选玩家：{candidates_str}。请开始竞选发言。",
            is_public=True
        )
        self.game.game_logs.append(log)
        
        # Reset acted status ONLY for candidates
        for p in self.game.players:
            if p.id in self.game.sheriff_candidate_ids:
                p.has_acted = False
            else:
                p.has_acted = True # Non-candidates don't act

    def process_action(self, action: ActionRequest) -> bool:
        player = next((p for p in self.game.players if p.id == action.player_id), None)
        if not player or player.id not in self.game.sheriff_candidate_ids:
            return False

        if action.type == ActionType.SPEECH:
            log = GameLog(
                id=str(uuid.uuid4()),
                day=self.game.day,
                phase=self.game.phase,
                content=f"{player.id}号(竞选发言): {action.content}",
                player_id=player.id,
                is_public=True
            )
            self.game.game_logs.append(log)
            player.has_acted = True
            return True
            
        elif action.type == ActionType.WITHDRAW:
            # Withdraw from election
            if player.id in self.game.sheriff_candidate_ids:
                self.game.sheriff_candidate_ids.remove(player.id)
                log = GameLog(
                    id=str(uuid.uuid4()),
                    day=self.game.day,
                    phase=self.game.phase,
                    content=f"{player.id}号退水。",
                    player_id=player.id,
                    is_public=True
                )
                self.game.game_logs.append(log)
            player.has_acted = True
            return True

        elif action.type == ActionType.SELF_EXPLODE:
            # Check if player is wolf
            if player.role not in [Role.WOLF, Role.WOLF_KING]:
                return False

            # Execute explosion
            player.is_alive = False
            self.game.dead_players.append(player.id)
            self.game.election_explode_count += 1

            # Remove from candidates list
            if player.id in self.game.sheriff_candidate_ids:
                self.game.sheriff_candidate_ids.remove(player.id)

            # Log explosion
            log = GameLog(
                id=str(uuid.uuid4()),
                day=self.game.day,
                phase=self.game.phase,
                content=f"{player.id}号玩家自爆！身份是{player.role.value}。",
                player_id=player.id,
                is_public=True,
                type="action",
                data={"action": "self_explode", "role": player.role.value}
            )
            self.game.game_logs.append(log)

            # Check for double explosion rule:
            # 若存在至少两个狼人参与警上，且竞选阶段先后自爆，则立即终止竞选流程
            wolf_candidates_count = len(self.game.election_wolf_candidates)
            if self.game.election_explode_count >= 2 and wolf_candidates_count >= 2:
                # 双自爆：竞选彻底取消，本局无警长
                self.game.pending_sheriff_election = False
                self.game.election_cancelled = True
                log = GameLog(
                    id=str(uuid.uuid4()),
                    day=self.game.day,
                    phase=self.game.phase,
                    content="狼人双自爆，警长竞选彻底取消！本局游戏无警长。",
                    is_public=True,
                    type="broadcast"
                )
                self.game.game_logs.append(log)
            else:
                # 单自爆：竞选推迟到明天
                self.game.pending_sheriff_election = True
                log = GameLog(
                    id=str(uuid.uuid4()),
                    day=self.game.day,
                    phase=self.game.phase,
                    content="狼人自爆，警长竞选推迟到明天。",
                    is_public=True,
                    type="broadcast"
                )
                self.game.game_logs.append(log)

            self.exploded = True
            player.has_acted = True
            return True
            
        return False

    def try_advance(self) -> GamePhase:
        # Check for explosion interrupt
        if getattr(self, 'exploded', False):
            return GamePhase.NIGHT_START

        # Check if all ORIGINAL candidates have acted (spoken or withdrawn)
        # Note: We iterate over players who ARE candidates currently or were?
        # The logic in on_enter set has_acted=False for candidates.
        # So we just check if any player with has_acted=False exists.
        
        pending_players = [p for p in self.game.players if not p.has_acted and p.is_alive]
        if not pending_players:
            if not self.game.sheriff_candidate_ids:
                 # All withdrew
                log = GameLog(
                    id=str(uuid.uuid4()),
                    day=self.game.day,
                    phase=self.game.phase,
                    content="所有竞选玩家退水，本局无警长。",
                    is_public=True
                )
                self.game.game_logs.append(log)
                return GamePhase.NIGHT_START
            return GamePhase.SHERIFF_VOTE
            
        return None