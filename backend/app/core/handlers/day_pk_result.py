"""平票PK结果阶段处理器"""
from typing import Optional
from app.core.phase_handler import PhaseHandler
from app.models.game_state import GamePhase
from app.models.action_model import ActionRequest


class DayPKResultHandler(PhaseHandler):
    def get_phase(self) -> GamePhase:
        return GamePhase.DAY_PK_RESULT

    def on_enter(self):
        vote_counts = self.count_votes(self.game.pk_votes, sheriff_weighted=True)

        content = self.format_vote_log(self.game.pk_votes, prefix="PK投票结果")
        self.add_log(content, data={"pk_votes": self.game.pk_votes, "sheriff_id": self.game.sheriff_id})

        self.banished_id = None
        winner_id, max_votes, candidates = self.resolve_vote_winner(vote_counts)

        if winner_id:
            self.banished_id = winner_id
            player = self.find_player(self.banished_id)
            player.is_alive = False
            self.game.dead_players.append(self.banished_id)
            self.add_log(f"PK结果：{self.banished_id}号玩家以{max_votes}票被放逐。")
        elif candidates:
            candidates_str = ", ".join([f"{pid}号" for pid in candidates])
            self.add_log(f"PK后仍然平票（{candidates_str}各{max_votes}票），无人出局。")
        else:
            self.add_log("无人投票，无人出局。")

        # 清理PK状态
        self.game.pk_candidates = []
        self.game.pk_votes = {}
        self.game.pk_round = 0

    def process_action(self, action: ActionRequest) -> bool:
        return False

    def try_advance(self) -> Optional[GamePhase]:
        if hasattr(self, 'banished_id') and self.banished_id:
            skill_phase = self.check_death_skills(self.banished_id, GamePhase.NIGHT_START)
            if skill_phase:
                return skill_phase
        return GamePhase.NIGHT_START
