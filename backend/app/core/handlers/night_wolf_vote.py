import random
from collections import Counter
from app.core.phase_handler import PhaseHandler
from app.models.game_state import GamePhase, ActionType, Role
from app.models.action_model import ActionRequest


class NightWolfVoteHandler(PhaseHandler):
    def get_phase(self) -> GamePhase:
        return GamePhase.NIGHT_WOLF_VOTE

    def on_enter(self):
        if self.game.wolf_revote_resolver_id:
            self.add_log(
                "狼人投票平票，系统随机指定一名狼人重新决定目标。",
                is_public=False,
                data=self.build_event_data(
                    "wolf_vote_revote_pending",
                    resolver_id=self.game.wolf_revote_resolver_id,
                    votes=dict(self.game.votes),
                ),
            )
            return

        wolf_ids = [p.id for p in self.game.players if p.role in (Role.WOLF, Role.WOLF_KING) and p.is_alive]
        self.add_log(
            "狼人请执行击杀目标。",
            is_public=False,
            data=self.build_event_data(
                "wolf_vote_started",
                participant_ids=wolf_ids,
            ),
        )
        self.game.votes = {}
        self.reset_actions(lambda p: p.role in (Role.WOLF, Role.WOLF_KING) and p.is_alive)

    def process_action(self, action: ActionRequest) -> bool:
        player = self.find_player(action.player_id)
        if not player or player.role not in (Role.WOLF, Role.WOLF_KING):
            return False
        if self.game.wolf_revote_resolver_id and player.id != self.game.wolf_revote_resolver_id:
            return False

        if action.type == ActionType.KILL:
            if not self.is_alive_target(action.target_id):
                return False
            self.game.votes[player.id] = action.target_id
            player.has_acted = True
            is_revote = self.game.wolf_revote_resolver_id == player.id
            if is_revote:
                self.game.wolf_revote_resolver_id = None
            self.add_log(
                f"{player.id}号 选择了击杀 {action.target_id}号",
                player_id=player.id,
                is_public=False,
                log_type="action",
                data=self.build_event_data(
                    "wolf_vote_cast",
                    action="kill",
                    voter_id=player.id,
                    target_id=action.target_id,
                    is_revote=is_revote,
                    votes=dict(self.game.votes),
                ),
            )
            return True

        return False

    def try_advance(self) -> GamePhase:
        if not self.all_acted(lambda p: p.role in (Role.WOLF, Role.WOLF_KING) and p.is_alive):
            return None

        vote_counts = Counter(self.game.votes.values())
        votes_snapshot = dict(self.game.votes)
        vote_counts_snapshot = dict(vote_counts)
        if not vote_counts:
            self.game.wolf_kill_target = None
        else:
            max_votes = vote_counts.most_common(1)[0][1]
            candidates = [pid for pid, c in vote_counts.items() if c == max_votes]
            if len(candidates) > 1:
                resolver = self._pick_revote_resolver()
                if resolver:
                    self.game.wolf_revote_resolver_id = resolver.id
                    resolver.has_acted = False
                    self.add_log(
                        f"狼人投票平票（{', '.join(f'{pid}号' for pid in candidates)}），"
                        f"随机指定 {resolver.id} 号狼人重新决定目标。",
                        is_public=False,
                        data=self.build_event_data(
                            "wolf_vote_tied",
                            candidate_ids=candidates,
                            resolver_id=resolver.id,
                            votes=votes_snapshot,
                            vote_counts=vote_counts_snapshot,
                        ),
                    )
                    return None
            self.game.wolf_kill_target = candidates[0]

        if self.game.wolf_kill_target:
            target = self.find_player(self.game.wolf_kill_target)
            if target:
                target.killed_by_wolf = True

        self.add_log(
            "狼人投票结果已确认。",
            is_public=False,
            data=self.build_event_data(
                "wolf_vote_resolved",
                target_id=self.game.wolf_kill_target,
                votes=votes_snapshot,
                vote_counts=vote_counts_snapshot,
            ),
        )

        return GamePhase.NIGHT_SEER

    def _pick_revote_resolver(self):
        wolves = [p for p in self.game.players if p.is_alive and p.role in (Role.WOLF, Role.WOLF_KING)]
        if not wolves:
            return None
        return random.choice(wolves)
