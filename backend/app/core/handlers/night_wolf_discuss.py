from app.core.phase_handler import PhaseHandler
from app.models.game_state import GamePhase, ActionType, WolfDiscussMessage, Role
from app.models.action_model import ActionRequest
import uuid


class NightWolfDiscussHandler(PhaseHandler):
    def get_phase(self) -> GamePhase:
        return GamePhase.NIGHT_WOLF_DISCUSS

    def on_enter(self):
        if not hasattr(self.game, 'wolf_discuss_round'):
            self.game.wolf_discuss_round = 1
        else:
            self.game.wolf_discuss_round += 1

        self.add_log(
            f"狼人讨论第 {self.game.wolf_discuss_round}/3 轮开始。",
            is_public=False,
        )
        self.reset_actions(lambda p: p.role in (Role.WOLF, Role.WOLF_KING) and p.is_alive)

    def process_action(self, action: ActionRequest) -> bool:
        player = self.find_player(action.player_id)
        if not player or player.role not in (Role.WOLF, Role.WOLF_KING):
            return False

        if action.type == ActionType.SPEECH:
            self.add_log(
                f"{player.id}号(狼人): {action.content}",
                player_id=player.id,
                is_public=False,
                log_type="speech",
            )
            self.game.wolf_discuss_messages.append(WolfDiscussMessage(
                id=str(uuid.uuid4()),
                speaker_id=player.id,
                content=action.content,
                round=self.game.wolf_discuss_round,
            ))
            player.has_acted = True
            return True

        if action.type == ActionType.PASS:
            player.has_acted = True
            return True

        return False

    def try_advance(self) -> GamePhase:
        if self.all_acted(lambda p: p.role in (Role.WOLF, Role.WOLF_KING) and p.is_alive):
            if self.game.wolf_discuss_round < 3:
                return GamePhase.NIGHT_WOLF_DISCUSS
            else:
                delattr(self.game, 'wolf_discuss_round')
                return GamePhase.NIGHT_WOLF_VOTE
        return None
