from collections import Counter
from typing import Optional
from app.core.phase_handler import PhaseHandler
from app.models.game_state import GamePhase, ActionType, GameLog, Role
from app.models.action_model import ActionRequest
from app.core.rules import Rules
import uuid

class DayVoteResultHandler(PhaseHandler):
    def get_phase(self) -> GamePhase:
        return GamePhase.DAY_VOTE_RESULT

    def on_enter(self):
        # 警长票权2倍：统计带权重的票数
        vote_counts = {}
        sheriff_id = self.game.sheriff_id

        # Ensure votes dict keys are integers
        votes_snapshot = {int(k): v for k, v in self.game.votes.items()}

        content = "投票结果：\n"
        for voter_id, target_id in sorted(votes_snapshot.items()):
            # 计算票权：警长为2票，其他为1票
            weight = 2 if voter_id == sheriff_id else 1
            weight_str = "(警长票x2)" if voter_id == sheriff_id else ""

            target_name = f"{target_id}号" if target_id != 0 else "弃票"
            content += f"{voter_id}号{weight_str} -> {target_name}\n"

            # 统计有效票数（非弃票）
            if target_id != 0:
                if target_id not in vote_counts:
                    vote_counts[target_id] = 0
                vote_counts[target_id] += weight

        # Log vote details with structured data
        log = GameLog(
            id=str(uuid.uuid4()),
            day=self.game.day,
            phase=self.game.phase,
            content=content,
            is_public=True,
            data={"votes": votes_snapshot, "sheriff_id": sheriff_id}
        )
        self.game.game_logs.append(log)

        # Determine banished player
        self.banished_id = None
        if vote_counts:
            # 找出最高票数
            max_votes = max(vote_counts.values())
            candidates = [pid for pid, c in vote_counts.items() if c == max_votes]

            if len(candidates) == 1:
                self.banished_id = candidates[0]
                # Kill the player
                player = next(p for p in self.game.players if p.id == self.banished_id)
                player.is_alive = False
                self.game.dead_players.append(self.banished_id)

                log = GameLog(
                    id=str(uuid.uuid4()),
                    day=self.game.day,
                    phase=self.game.phase,
                    content=f"{self.banished_id}号玩家以{max_votes}票被放逐。",
                    is_public=True
                )
                self.game.game_logs.append(log)
            else:
                # 平票 - 进入PK环节
                candidates_str = ", ".join([f"{pid}号" for pid in candidates])
                log = GameLog(
                    id=str(uuid.uuid4()),
                    day=self.game.day,
                    phase=self.game.phase,
                    content=f"平票（{candidates_str}各{max_votes}票），进入PK环节。",
                    is_public=True
                )
                self.game.game_logs.append(log)

                # 设置PK候选人
                self.game.pk_candidates = candidates
                self.game.pk_round = 1
                self.need_pk = True
        else:
            log = GameLog(
                id=str(uuid.uuid4()),
                day=self.game.day,
                phase=self.game.phase,
                content="无人投票，无人出局。",
                is_public=True
            )
            self.game.game_logs.append(log)

    def process_action(self, action: ActionRequest) -> bool:
        return False

    def try_advance(self) -> Optional[GamePhase]:
        # Check for death skills if someone died
        if hasattr(self, 'banished_id') and self.banished_id:
            player = next(p for p in self.game.players if p.id == self.banished_id)
            
            # Check Hunter/Wolf King
            if player.role in [Role.HUNTER, Role.WOLF_KING]:
                if Rules.can_shoot(player, "vote"):
                    self.game.next_phase_after_skill = GamePhase.NIGHT_START # Return to Night Start (next day)
                    return GamePhase.HUNTER_SKILL
            
            # Check Sheriff
            if player.is_sheriff:
                self.game.next_phase_after_skill = GamePhase.NIGHT_START
                return GamePhase.SHERIFF_TRANSFER

        # If no skills or no one died, go to Night Start
        return GamePhase.NIGHT_START