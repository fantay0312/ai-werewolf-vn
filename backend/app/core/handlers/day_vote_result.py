from typing import Optional
from app.core.phase_handler import PhaseHandler
from app.models.game_state import GamePhase, Role
from app.models.action_model import ActionRequest


class DayVoteResultHandler(PhaseHandler):
    def get_phase(self) -> GamePhase:
        return GamePhase.DAY_VOTE_RESULT

    def on_enter(self):
        votes_snapshot = {int(k): v for k, v in self.game.votes.items()}
        vote_counts = self.count_votes(votes_snapshot, sheriff_weighted=True)

        # Log vote details
        content = self.format_vote_log(votes_snapshot)
        self.add_log(content, data={"votes": votes_snapshot, "sheriff_id": self.game.sheriff_id})

        # Determine banished player
        self.banished_id = None
        winner_id, max_votes, candidates = self.resolve_vote_winner(vote_counts)

        if winner_id:
            self.banished_id = winner_id
            player = self.find_player(self.banished_id)
            player.is_alive = False
            self.game.dead_players.append(self.banished_id)
            self.add_log(f"{self.banished_id}号玩家以{max_votes}票被放逐。")
        elif candidates:
            # 平票 - 进入PK环节
            candidates_str = ", ".join([f"{pid}号" for pid in candidates])
            self.add_log(f"平票（{candidates_str}各{max_votes}票），进入PK环节。")
            self.game.pk_candidates = candidates
            self.game.pk_round = 1
            self.need_pk = True
        else:
            self.add_log("无人投票，无人出局。")

    def process_action(self, action: ActionRequest) -> bool:
        return False

    def try_advance(self) -> Optional[GamePhase]:
        if hasattr(self, 'banished_id') and self.banished_id:
            skill_phase = self.check_death_skills(self.banished_id, GamePhase.NIGHT_START)
            if skill_phase:
                return skill_phase

        if hasattr(self, 'need_pk') and self.need_pk:
            return GamePhase.DAY_PK_SPEECH

        return GamePhase.NIGHT_START
