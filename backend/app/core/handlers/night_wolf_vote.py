from collections import Counter
from app.core.phase_handler import PhaseHandler
from app.models.game_state import GamePhase, ActionType, Role
from app.models.action_model import ActionRequest


class NightWolfVoteHandler(PhaseHandler):
    def get_phase(self) -> GamePhase:
        return GamePhase.NIGHT_WOLF_VOTE

    def on_enter(self):
        self.add_log("狼人请执行击杀目标。", is_public=False)
        self.game.votes = {}
        self.reset_actions(lambda p: p.role in (Role.WOLF, Role.WOLF_KING) and p.is_alive)

    def process_action(self, action: ActionRequest) -> bool:
        player = self.find_player(action.player_id)
        if not player or player.role not in (Role.WOLF, Role.WOLF_KING):
            return False

        if action.type == ActionType.KILL:
            if action.target_id is None:
                return False
            self.game.votes[player.id] = action.target_id
            player.has_acted = True
            self.add_log(
                f"{player.id}号 选择了击杀 {action.target_id}号",
                player_id=player.id,
                is_public=False,
            )
            return True

        return False

    def try_advance(self) -> GamePhase:
        if not self.all_acted(lambda p: p.role in (Role.WOLF, Role.WOLF_KING) and p.is_alive):
            return None

        vote_counts = Counter(self.game.votes.values())
        if not vote_counts:
            self.game.wolf_kill_target = None
        else:
            max_votes = vote_counts.most_common(1)[0][1]
            candidates = [pid for pid, c in vote_counts.items() if c == max_votes]
            self.game.wolf_kill_target = candidates[0]

        if self.game.wolf_kill_target:
            target = self.find_player(self.game.wolf_kill_target)
            if target:
                target.killed_by_wolf = True

        return GamePhase.NIGHT_SEER
