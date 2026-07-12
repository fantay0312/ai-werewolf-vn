from app.core.phase_handler import PhaseHandler
from app.models.game_state import GamePhase, ActionType, Role
from app.models.action_model import ActionRequest


class SheriffElectionHandler(PhaseHandler):
    def get_phase(self) -> GamePhase:
        return GamePhase.SHERIFF_ELECTION

    def on_enter(self):
        if self.game.election_cancelled:
            self.add_log(
                "由于狼人双自爆，本局游戏无警长。",
                data=self.build_event_data(
                    "sheriff_election_cancelled",
                    reason="double_self_explode",
                    election_explode_count=self.game.election_explode_count,
                    sheriff_candidate_ids=list(self.game.sheriff_candidate_ids),
                    next_phase_hint=GamePhase.NIGHT_START.value,
                ),
            )
            return

        participant_ids = [player.id for player in self.game.players if player.is_alive]
        self.add_log(
            "现在开始警长竞选。想要竞选警长的玩家请上警。",
            data=self.build_event_data(
                "sheriff_election_started",
                participant_ids=participant_ids,
                participant_count=len(participant_ids),
                sheriff_candidate_ids=[],
                accepted_actions=[ActionType.RUN_FOR_SHERIFF.value, ActionType.PASS.value],
                next_phase_if_has_candidates=GamePhase.SHERIFF_SPEECH.value,
                next_phase_if_no_candidates=GamePhase.NIGHT_START.value,
            ),
        )
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
                player.has_acted = True
                acted_player_ids, pending_player_ids = self._election_progress()
                all_acted = self.all_acted()
                self.add_log(
                    f"{player.id}号玩家参与竞选。",
                    player_id=player.id,
                    log_type="action",
                    data=self.build_event_data(
                        "sheriff_candidacy_declared",
                        action=ActionType.RUN_FOR_SHERIFF.value,
                        player_id=player.id,
                        sheriff_candidate_ids=list(self.game.sheriff_candidate_ids),
                        candidate_count=len(self.game.sheriff_candidate_ids),
                        acted_player_ids=acted_player_ids,
                        pending_player_ids=pending_player_ids,
                        acted_count=len(acted_player_ids),
                        pending_count=len(pending_player_ids),
                        all_acted=all_acted,
                        next_phase_hint=self._closed_phase_hint() if all_acted else None,
                    ),
                )
            else:
                player.has_acted = True
            return True

        if action.type == ActionType.PASS:
            player.has_acted = True
            acted_player_ids, pending_player_ids = self._election_progress()
            all_acted = self.all_acted()
            self.add_log(
                f"{player.id}号玩家选择不上警。",
                player_id=player.id,
                log_type="action",
                data=self.build_event_data(
                    "sheriff_election_passed",
                    action=ActionType.PASS.value,
                    player_id=player.id,
                    sheriff_candidate_ids=list(self.game.sheriff_candidate_ids),
                    candidate_count=len(self.game.sheriff_candidate_ids),
                    acted_player_ids=acted_player_ids,
                    pending_player_ids=pending_player_ids,
                    acted_count=len(acted_player_ids),
                    pending_count=len(pending_player_ids),
                    all_acted=all_acted,
                    next_phase_hint=self._closed_phase_hint() if all_acted else None,
                ),
            )
            return True

        return False

    def try_advance(self) -> GamePhase:
        if self.game.election_cancelled:
            return GamePhase.NIGHT_START

        if self.all_acted():
            if not self.game.sheriff_candidate_ids:
                self.add_log(
                    "无人竞选警长，本局游戏无警长。",
                    data=self.build_event_data(
                        "sheriff_election_closed",
                        outcome="no_candidates",
                        sheriff_candidate_ids=[],
                        candidate_count=0,
                        next_phase_hint=GamePhase.NIGHT_START.value,
                    ),
                )
                return GamePhase.NIGHT_START
            self.add_log(
                "警长竞选报名结束，进入竞选发言阶段。",
                data=self.build_event_data(
                    "sheriff_election_closed",
                    outcome="speech_required",
                    sheriff_candidate_ids=list(self.game.sheriff_candidate_ids),
                    candidate_count=len(self.game.sheriff_candidate_ids),
                    next_phase_hint=GamePhase.SHERIFF_SPEECH.value,
                ),
            )
            return GamePhase.SHERIFF_SPEECH
        return None

    def _election_progress(self) -> tuple[list[int], list[int]]:
        acted_player_ids = sorted(player.id for player in self.game.players if player.is_alive and player.has_acted)
        pending_player_ids = sorted(player.id for player in self.game.players if player.is_alive and not player.has_acted)
        return acted_player_ids, pending_player_ids

    def _closed_phase_hint(self) -> str:
        if self.game.sheriff_candidate_ids:
            return GamePhase.SHERIFF_SPEECH.value
        return GamePhase.NIGHT_START.value
