from collections import Counter
from app.core.phase_handler import PhaseHandler
from app.models.game_state import GamePhase, ActionType
from app.models.action_model import ActionRequest


class SheriffVoteHandler(PhaseHandler):
    def get_phase(self) -> GamePhase:
        return GamePhase.SHERIFF_VOTE

    def on_enter(self):
        candidates = sorted(self.game.sheriff_candidate_ids)
        eligible_voter_ids = [
            p.id for p in self.game.players if p.is_alive and p.id not in self.game.sheriff_candidate_ids
        ]
        candidates_str = ", ".join([f"{pid}号" for pid in candidates])
        self.add_log(
            f"请未竞选的玩家在 {candidates_str} 中投票选出警长。",
            data=self.build_event_data(
                "sheriff_vote_started",
                action="prompt",
                candidate_ids=candidates,
                eligible_voter_ids=eligible_voter_ids,
                eligible_target_ids=candidates,
                allow_abstain=True,
                accepted_actions=[ActionType.VOTE.value],
                next_phase_hint=GamePhase.NIGHT_START.value,
            ),
        )

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
            target_id = None
            is_abstain = action.target_id is None
            if action.target_id is None:
                self.game.votes[player.id] = 0
                target_id = 0
            elif action.target_id in self.game.sheriff_candidate_ids:
                self.game.votes[player.id] = action.target_id
                target_id = action.target_id
            else:
                return False
            player.has_acted = True
            self.add_log(
                f"{player.id}号完成警长投票。",
                player_id=player.id,
                is_public=False,
                log_type="action",
                data=self.build_event_data(
                    "sheriff_vote_cast",
                    action="vote",
                    voter_id=player.id,
                    target_id=target_id,
                    target_label="弃票" if target_id == 0 else f"{target_id}号",
                    is_abstain=is_abstain,
                    target_valid=True,
                    candidate_ids=sorted(self.game.sheriff_candidate_ids),
                    votes=dict(self.game.votes),
                    vote_progress={
                        "acted_player_ids": sorted(
                            p.id
                            for p in self.game.players
                            if p.is_alive and p.id not in self.game.sheriff_candidate_ids and p.has_acted
                        ),
                        "pending_player_ids": sorted(
                            p.id
                            for p in self.game.players
                            if p.is_alive and p.id not in self.game.sheriff_candidate_ids and not p.has_acted
                        ),
                    },
                    next_phase_hint=GamePhase.NIGHT_START.value,
                ),
            )
            return True

        return False

    def try_advance(self) -> GamePhase:
        eligible = [p for p in self.game.players if p.is_alive and p.id not in self.game.sheriff_candidate_ids]
        if not all(p.has_acted for p in eligible):
            return None

        # Tally votes
        vote_counts = Counter([t for t in self.game.votes.values() if t != 0])
        votes_snapshot = dict(self.game.votes)
        vote_counts_snapshot = dict(vote_counts)

        # Log votes
        content = "警长投票结果：\n"
        for voter_id, target_id in self.game.votes.items():
            target_name = f"{target_id}号" if target_id != 0 else "弃票"
            content += f"{voter_id}号 -> {target_name}\n"
        self.add_log(
            content,
            data=self.build_event_data(
                "sheriff_vote_tallied",
                action="tally",
                candidate_ids=sorted(self.game.sheriff_candidate_ids),
                votes=votes_snapshot,
                vote_counts=vote_counts_snapshot,
                abstain_voter_ids=sorted(voter_id for voter_id, target_id in votes_snapshot.items() if target_id == 0),
                abstain_count=sum(1 for target_id in votes_snapshot.values() if target_id == 0),
                total_ballots=len(votes_snapshot),
                counted_ballots=sum(1 for target_id in votes_snapshot.values() if target_id != 0),
            ),
        )

        if vote_counts:
            max_votes = vote_counts.most_common(1)[0][1]
            winners = [pid for pid, c in vote_counts.items() if c == max_votes]

            if len(winners) == 1:
                sheriff_id = winners[0]
                self.game.sheriff_id = sheriff_id
                sheriff = self.find_player(sheriff_id)
                sheriff.is_sheriff = True
                self.add_log(
                    f"{sheriff_id}号当选警长！",
                    data=self.build_event_data(
                        "sheriff_elected",
                        sheriff_id=sheriff_id,
                        candidate_ids=winners,
                        vote_count=max_votes,
                        votes=votes_snapshot,
                        vote_counts=vote_counts_snapshot,
                        next_phase=GamePhase.NIGHT_START.value,
                    ),
                )
            else:
                self.add_log(
                    "平票，本局无警长。",
                    data=self.build_event_data(
                        "sheriff_vote_tied",
                        candidate_ids=winners,
                        vote_count=max_votes,
                        votes=votes_snapshot,
                        vote_counts=vote_counts_snapshot,
                        next_phase=GamePhase.NIGHT_START.value,
                    ),
                )
        else:
            self.add_log(
                "无人投票，本局无警长。",
                data=self.build_event_data(
                    "sheriff_vote_empty",
                    candidate_ids=sorted(self.game.sheriff_candidate_ids),
                    votes=votes_snapshot,
                    vote_counts=vote_counts_snapshot,
                    next_phase=GamePhase.NIGHT_START.value,
                ),
            )

        return GamePhase.NIGHT_START
