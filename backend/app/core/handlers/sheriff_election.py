from app.core.phase_handler import PhaseHandler
from app.models.game_state import GamePhase, ActionType, GameLog, Role
from app.models.action_model import ActionRequest
import uuid

class SheriffElectionHandler(PhaseHandler):
    def get_phase(self) -> GamePhase:
        return GamePhase.SHERIFF_ELECTION

    def on_enter(self):
        # 检查是否已经被双自爆取消
        if self.game.election_cancelled:
            log = GameLog(
                id=str(uuid.uuid4()),
                day=self.game.day,
                phase=self.game.phase,
                content="由于狼人双自爆，本局游戏无警长。",
                is_public=True
            )
            self.game.game_logs.append(log)
            return

        log = GameLog(
            id=str(uuid.uuid4()),
            day=self.game.day,
            phase=self.game.phase,
            content="现在开始警长竞选。想要竞选警长的玩家请上警。",
            is_public=True
        )
        self.game.game_logs.append(log)

        self.game.sheriff_candidate_ids = []

        for p in self.game.players:
            if p.is_alive:
                p.has_acted = False

    def process_action(self, action: ActionRequest) -> bool:
        # 如果竞选已取消，不处理任何动作
        if self.game.election_cancelled:
            return False

        player = next((p for p in self.game.players if p.id == action.player_id), None)
        if not player or not player.is_alive:
            return False

        if action.type == ActionType.RUN_FOR_SHERIFF:
            if player.id not in self.game.sheriff_candidate_ids:
                self.game.sheriff_candidate_ids.append(player.id)
                # 跟踪狼人候选人（用于双自爆规则判定）
                if player.role in [Role.WOLF, Role.WOLF_KING]:
                    if player.id not in self.game.election_wolf_candidates:
                        self.game.election_wolf_candidates.append(player.id)
                log = GameLog(
                    id=str(uuid.uuid4()),
                    day=self.game.day,
                    phase=self.game.phase,
                    content=f"{player.id}号玩家参与竞选。",
                    player_id=player.id,
                    is_public=True
                )
                self.game.game_logs.append(log)
            player.has_acted = True
            return True

        elif action.type == ActionType.PASS:
            # Choose not to run
            player.has_acted = True
            return True

        return False

    def try_advance(self) -> GamePhase:
        # 如果竞选已取消（双自爆），直接跳过
        if self.game.election_cancelled:
            return GamePhase.NIGHT_START

        alive_players = [p for p in self.game.players if p.is_alive]
        if all(p.has_acted for p in alive_players):
            if not self.game.sheriff_candidate_ids:
                log = GameLog(
                    id=str(uuid.uuid4()),
                    day=self.game.day,
                    phase=self.game.phase,
                    content="无人竞选警长，本局游戏无警长。",
                    is_public=True
                )
                self.game.game_logs.append(log)
                return GamePhase.NIGHT_START
            else:
                return GamePhase.SHERIFF_SPEECH
        return None