from app.core.phase_handler import PhaseHandler
from app.models.game_state import GamePhase, ActionType, Role
from app.models.action_model import ActionRequest


class SheriffSpeechHandler(PhaseHandler):
    def get_phase(self) -> GamePhase:
        return GamePhase.SHERIFF_SPEECH

    def on_enter(self):
        candidates = sorted(self.game.sheriff_candidate_ids)
        candidates_str = ", ".join([f"{pid}号" for pid in candidates])
        self.add_log(f"竞选玩家：{candidates_str}。请开始竞选发言。")

        for p in self.game.players:
            p.has_acted = p.id not in self.game.sheriff_candidate_ids

    def process_action(self, action: ActionRequest) -> bool:
        player = self.find_player(action.player_id)
        if not player or player.id not in self.game.sheriff_candidate_ids:
            return False

        if action.type == ActionType.SPEECH:
            self.add_log(
                f"{player.id}号(竞选发言): {action.content}",
                player_id=player.id,
            )
            player.has_acted = True
            return True

        if action.type == ActionType.WITHDRAW:
            if player.id in self.game.sheriff_candidate_ids:
                self.game.sheriff_candidate_ids.remove(player.id)
                self.add_log(f"{player.id}号退水。", player_id=player.id)
            player.has_acted = True
            return True

        if action.type == ActionType.SELF_EXPLODE:
            if player.role not in (Role.WOLF, Role.WOLF_KING):
                return False

            player.is_alive = False
            self.game.dead_players.append(player.id)
            self.game.election_explode_count += 1

            if player.id in self.game.sheriff_candidate_ids:
                self.game.sheriff_candidate_ids.remove(player.id)

            self.add_log(
                f"{player.id}号玩家自爆！身份是{player.role.value}。",
                player_id=player.id,
                log_type="action",
                data={"action": "self_explode", "role": player.role.value},
            )

            wolf_candidates_count = len(self.game.election_wolf_candidates)
            if self.game.election_explode_count >= 2 and wolf_candidates_count >= 2:
                self.game.pending_sheriff_election = False
                self.game.election_cancelled = True
                self.add_log("狼人双自爆，警长竞选彻底取消！本局游戏无警长。", log_type="broadcast")
            else:
                self.game.pending_sheriff_election = True
                self.add_log("狼人自爆，警长竞选推迟到明天。", log_type="broadcast")

            self.exploded = True
            player.has_acted = True
            return True

        return False

    def try_advance(self) -> GamePhase:
        if getattr(self, 'exploded', False):
            return GamePhase.NIGHT_START

        pending = [p for p in self.game.players if not p.has_acted and p.is_alive]
        if not pending:
            if not self.game.sheriff_candidate_ids:
                self.add_log("所有竞选玩家退水，本局无警长。")
                return GamePhase.NIGHT_START
            return GamePhase.SHERIFF_VOTE

        return None
