from collections import Counter
from app.core.phase_handler import PhaseHandler
from app.models.game_state import GamePhase, ActionType
from app.models.action_model import ActionRequest


class SheriffVoteHandler(PhaseHandler):
    def get_phase(self) -> GamePhase:
        return GamePhase.SHERIFF_VOTE

    def on_enter(self):
        candidates = sorted(self.game.sheriff_candidate_ids)
        candidates_str = ", ".join([f"{pid}号" for pid in candidates])
        self.add_log(f"请未竞选的玩家在 {candidates_str} 中投票选出警长。")

        self.game.votes = {}
        for p in self.game.players:
            if p.is_alive:
                p.has_acted = p.id in self.game.sheriff_candidate_ids

    def process_action(self, action: ActionRequest) -> bool:
        player = self.find_alive_player(action.player_id)
        if not player:
            return False
        if player.id in self.game.sheriff_candidate_ids:
            return False

        if action.type == ActionType.VOTE:
            if action.target_id is None:
                self.game.votes[player.id] = 0
            elif action.target_id in self.game.sheriff_candidate_ids:
                self.game.votes[player.id] = action.target_id
            else:
                return False
            player.has_acted = True
            return True

        return False

    def try_advance(self) -> GamePhase:
        eligible = [p for p in self.game.players if p.is_alive and p.id not in self.game.sheriff_candidate_ids]
        if not all(p.has_acted for p in eligible):
            return None

        # Tally votes
        vote_counts = Counter([t for t in self.game.votes.values() if t != 0])

        # Log votes
        content = "警长投票结果：\n"
        for voter_id, target_id in self.game.votes.items():
            target_name = f"{target_id}号" if target_id != 0 else "弃票"
            content += f"{voter_id}号 -> {target_name}\n"
        self.add_log(content)

        if vote_counts:
            max_votes = vote_counts.most_common(1)[0][1]
            winners = [pid for pid, c in vote_counts.items() if c == max_votes]

            if len(winners) == 1:
                sheriff_id = winners[0]
                self.game.sheriff_id = sheriff_id
                sheriff = self.find_player(sheriff_id)
                sheriff.is_sheriff = True
                self.add_log(f"{sheriff_id}号当选警长！")
            else:
                self.add_log("平票，本局无警长。")
        else:
            self.add_log("无人投票，本局无警长。")

        return GamePhase.NIGHT_START
