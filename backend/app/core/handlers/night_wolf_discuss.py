from app.core.phase_handler import PhaseHandler
from app.models.game_state import GamePhase, ActionType, WolfDiscussMessage, Role
from app.models.action_model import ActionRequest
import re
import uuid


PLAYER_MENTION_PATTERN = re.compile(r"(\d+)号")


class NightWolfDiscussHandler(PhaseHandler):
    def get_phase(self) -> GamePhase:
        return GamePhase.NIGHT_WOLF_DISCUSS

    def on_enter(self):
        if not hasattr(self.game, 'wolf_discuss_round'):
            self.game.wolf_discuss_round = 1
        else:
            self.game.wolf_discuss_round += 1

        wolf_ids = [p.id for p in self.game.players if p.role in (Role.WOLF, Role.WOLF_KING) and p.is_alive]
        self.add_log(
            f"狼人讨论第 {self.game.wolf_discuss_round}/3 轮开始。",
            is_public=False,
            data=self.build_event_data(
                "wolf_discuss_round_started",
                round=self.game.wolf_discuss_round,
                total_rounds=3,
                participant_ids=wolf_ids,
            ),
        )
        self.reset_actions(lambda p: p.role in (Role.WOLF, Role.WOLF_KING) and p.is_alive)

    def process_action(self, action: ActionRequest) -> bool:
        player = self.find_player(action.player_id)
        if not player or player.role not in (Role.WOLF, Role.WOLF_KING):
            return False

        if action.type == ActionType.SPEECH:
            message_id = str(uuid.uuid4())
            mentioned_player_ids = self._extract_player_mentions(action.content)
            self.add_log(
                f"{player.id}号(狼人): {action.content}",
                player_id=player.id,
                is_public=False,
                log_type="speech",
                data=self.build_event_data(
                    "wolf_discuss_speech",
                    action="speech",
                    speaker_id=player.id,
                    round=self.game.wolf_discuss_round,
                    message_id=message_id,
                    mentioned_player_ids=mentioned_player_ids,
                ),
            )
            self.game.wolf_discuss_messages.append(WolfDiscussMessage(
                id=message_id,
                speaker_id=player.id,
                content=action.content,
                round=self.game.wolf_discuss_round,
            ))
            player.has_acted = True
            return True

        if action.type == ActionType.PASS:
            player.has_acted = True
            self.add_log(
                f"{player.id}号(狼人)结束本轮讨论。",
                player_id=player.id,
                is_public=False,
                log_type="action",
                data=self.build_event_data(
                    "wolf_discuss_pass",
                    action="pass",
                    speaker_id=player.id,
                    round=self.game.wolf_discuss_round,
                ),
            )
            return True

        return False

    def try_advance(self) -> GamePhase:
        if self.all_acted(lambda p: p.role in (Role.WOLF, Role.WOLF_KING) and p.is_alive):
            if self.game.wolf_discuss_round < 3:
                self.add_log(
                    f"狼人讨论第 {self.game.wolf_discuss_round} 轮结束。",
                    is_public=False,
                    data=self.build_event_data(
                        "wolf_discuss_round_completed",
                        round=self.game.wolf_discuss_round,
                        next_round=self.game.wolf_discuss_round + 1,
                    ),
                )
                return GamePhase.NIGHT_WOLF_DISCUSS
            else:
                self.add_log(
                    "狼人讨论结束，进入投票阶段。",
                    is_public=False,
                    data=self.build_event_data(
                        "wolf_discuss_completed",
                        round=self.game.wolf_discuss_round,
                    ),
                )
                delattr(self.game, 'wolf_discuss_round')
                return GamePhase.NIGHT_WOLF_VOTE
        return None

    def _extract_player_mentions(self, content: str | None) -> list[int]:
        if not content:
            return []
        seen = []
        for match in PLAYER_MENTION_PATTERN.findall(content):
            player_id = int(match)
            if player_id not in seen:
                seen.append(player_id)
        return seen
