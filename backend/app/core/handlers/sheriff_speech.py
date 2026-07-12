from typing import Optional

from app.core.handlers.turn_window import TurnWindowHandler
from app.models.game_state import DeathCause, GamePhase, ActionType, Role
from app.models.action_model import ActionRequest


class SheriffSpeechHandler(TurnWindowHandler):
    speech_event = "sheriff_speech"
    turn_end_event = "sheriff_speech_turn_end"

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
        if super().process_action(action):
            return True

        player = self._current_turn_player(action.player_id)
        if not player:
            return False

        speaker_index = self.game.current_speaker_index

        if action.type == ActionType.WITHDRAW:
            self.game.sheriff_candidate_ids.remove(player.id)
            next_speaker = self._complete_turn(player)
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

            self.record_death(player, DeathCause.SELF_EXPLODE)
            if player.id not in self.game.dead_players:
                self.game.dead_players.append(player.id)
            self.game.election_explode_count += 1

            if player.id in self.game.sheriff_candidate_ids:
                self.game.sheriff_candidate_ids.remove(player.id)

            next_speaker = self._complete_turn(player)

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

            if self.evaluate_win_condition():
                self.exploded = True
                return True

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
            return True

        return False

    def try_advance(self) -> Optional[GamePhase]:
        if self.game.winner:
            return GamePhase.GAME_END
        if getattr(self, "exploded", False):
            return GamePhase.NIGHT_START
        return super().try_advance()

    def _allowed_turn_actions(self) -> set[ActionType]:
        return {ActionType.SPEECH}

    def _valid_speaker_ids(self) -> Optional[list[int]]:
        return self.game.sheriff_candidate_ids

    def _is_eligible_speaker(self, player) -> bool:
        return player.id in self.game.sheriff_candidate_ids

    def _speech_content(self, player, action: ActionRequest) -> str:
        return f"{player.id}号(竞选发言): {action.content}"

    def _turn_end_content(self, player) -> str:
        return f"{player.id}号结束竞选发言。"

    def _turn_event_fields(self) -> dict:
        return {"candidate_ids": sorted(self.game.sheriff_candidate_ids)}

    def _on_window_finished(self) -> GamePhase:
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
