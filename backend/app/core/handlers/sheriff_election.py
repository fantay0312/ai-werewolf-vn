from app.core.phase_handler import PhaseHandler
from app.models.game_state import GamePhase, ActionType, Role
from app.models.action_model import ActionRequest


class SheriffElectionHandler(PhaseHandler):
    def get_phase(self) -> GamePhase:
        return GamePhase.SHERIFF_ELECTION

    def on_enter(self):
        if self.game.election_cancelled:
            self.add_log("由于狼人双自爆，本局游戏无警长。")
            return

        self.add_log("现在开始警长竞选。想要竞选警长的玩家请上警。")
        self.game.sheriff_candidate_ids = []
        self.reset_actions()

    def process_action(self, action: ActionRequest) -> bool:
        if self.game.election_cancelled:
            return False

        player = self.find_alive_player(action.player_id)
        if not player:
            return False

        if action.type == ActionType.RUN_FOR_SHERIFF:
            if player.id not in self.game.sheriff_candidate_ids:
                self.game.sheriff_candidate_ids.append(player.id)
                if player.role in (Role.WOLF, Role.WOLF_KING):
                    if player.id not in self.game.election_wolf_candidates:
                        self.game.election_wolf_candidates.append(player.id)
                self.add_log(f"{player.id}号玩家参与竞选。", player_id=player.id)
            player.has_acted = True
            return True

        if action.type == ActionType.PASS:
            player.has_acted = True
            return True

        return False

    def try_advance(self) -> GamePhase:
        if self.game.election_cancelled:
            return GamePhase.NIGHT_START

        if self.all_acted():
            if not self.game.sheriff_candidate_ids:
                self.add_log("无人竞选警长，本局游戏无警长。")
                return GamePhase.NIGHT_START
            return GamePhase.SHERIFF_SPEECH
        return None
