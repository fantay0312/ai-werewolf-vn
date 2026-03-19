from app.core.phase_handler import PhaseHandler
from app.models.game_state import DeathCause, GamePhase, ActionType, Role
from app.models.action_model import ActionRequest


class SheriffSpeechHandler(PhaseHandler):
    def get_phase(self) -> GamePhase:
        return GamePhase.SHERIFF_SPEECH

    def on_enter(self):
        candidates = sorted(self.game.sheriff_candidate_ids)
        candidates_str = ", ".join([f"{pid}号" for pid in candidates])
        self.prime_speaking_window(candidates, participant_ids=candidates)
        self.add_log(
            f"竞选玩家：{candidates_str}。请开始竞选发言。",
            data=self.build_event_data(
                "sheriff_speech_started",
                candidate_ids=candidates,
                current_speaker_id=self.current_speaker_id(),
            ),
        )

    def process_action(self, action: ActionRequest) -> bool:
        player = self.find_player(action.player_id)
        if (
            not player
            or player.id not in self.game.sheriff_candidate_ids
            or not self.is_current_speaker(action.player_id)
        ):
            return False

        speaker_index = self.game.current_speaker_index

        if action.type == ActionType.SPEECH:
            player.has_acted = True
            self.advance_speaker_to_valid(self.game.sheriff_candidate_ids)
            next_speaker = self.activate_current_speaker()
            self.add_log(
                f"{player.id}号(竞选发言): {action.content}",
                player_id=player.id,
                log_type="speech",
                data=self.build_event_data(
                    "sheriff_speech",
                    action="speech",
                    speaker_id=player.id,
                    speaker_index=speaker_index,
                    candidate_ids=sorted(self.game.sheriff_candidate_ids),
                    next_speaker_id=next_speaker.id if next_speaker else None,
                ),
            )
            return True

        if action.type == ActionType.WITHDRAW:
            if player.id in self.game.sheriff_candidate_ids:
                self.game.sheriff_candidate_ids.remove(player.id)
            player.has_acted = True
            self.advance_speaker_to_valid(self.game.sheriff_candidate_ids)
            next_speaker = self.activate_current_speaker()
            self.add_log(
                f"{player.id}号退水。",
                player_id=player.id,
                log_type="action",
                data=self.build_event_data(
                    "sheriff_withdraw",
                    action="withdraw",
                    speaker_id=player.id,
                    speaker_index=speaker_index,
                    remaining_candidate_ids=sorted(self.game.sheriff_candidate_ids),
                    next_speaker_id=next_speaker.id if next_speaker else None,
                ),
            )
            return True

        if action.type == ActionType.SELF_EXPLODE:
            if player.role not in (Role.WOLF, Role.WOLF_KING):
                return False

            player.is_alive = False
            player.death_cause = DeathCause.SELF_EXPLODE
            if player.id not in self.game.dead_players:
                self.game.dead_players.append(player.id)
            self.game.election_explode_count += 1

            if player.id in self.game.sheriff_candidate_ids:
                self.game.sheriff_candidate_ids.remove(player.id)

            self.advance_speaker_to_valid(self.game.sheriff_candidate_ids)
            next_speaker = self.activate_current_speaker()

            self.add_log(
                f"{player.id}号玩家自爆！身份是{player.role.value}。",
                player_id=player.id,
                log_type="action",
                data=self.build_event_data(
                    "sheriff_self_explode",
                    action="self_explode",
                    role=player.role.value,
                    speaker_id=player.id,
                    speaker_index=speaker_index,
                    remaining_candidate_ids=sorted(self.game.sheriff_candidate_ids),
                    next_speaker_id=next_speaker.id if next_speaker else None,
                ),
            )

            wolf_candidates_count = len(self.game.election_wolf_candidates)
            if self.game.election_explode_count >= 2 and wolf_candidates_count >= 2:
                self.game.pending_sheriff_election = False
                self.game.election_cancelled = True
                self.add_log(
                    "狼人双自爆，警长竞选彻底取消！本局游戏无警长。",
                    log_type="broadcast",
                    data=self.build_event_data(
                        "sheriff_election_cancelled",
                        action="cancel",
                        election_explode_count=self.game.election_explode_count,
                    ),
                )
            else:
                self.game.pending_sheriff_election = True
                self.add_log(
                    "狼人自爆，警长竞选推迟到明天。",
                    log_type="broadcast",
                    data=self.build_event_data(
                        "sheriff_election_postponed",
                        action="postpone",
                        election_explode_count=self.game.election_explode_count,
                    ),
                )

            self.exploded = True
            player.has_acted = True
            return True

        return False

    def try_advance(self) -> GamePhase:
        if getattr(self, 'exploded', False):
            return GamePhase.NIGHT_START

        if self.all_speakers_done():
            if not self.game.sheriff_candidate_ids:
                self.add_log(
                    "所有竞选玩家退水，本局无警长。",
                    data=self.build_event_data(
                        "sheriff_election_empty",
                        candidate_ids=[],
                    ),
                )
                return GamePhase.NIGHT_START
            return GamePhase.SHERIFF_VOTE

        return None
