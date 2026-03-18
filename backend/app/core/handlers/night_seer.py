from app.core.phase_handler import PhaseHandler
from app.models.game_state import GamePhase, ActionType, Role
from app.models.action_model import ActionRequest


class NightSeerHandler(PhaseHandler):
    def get_phase(self) -> GamePhase:
        return GamePhase.NIGHT_SEER

    def on_enter(self):
        self.add_log("预言家请查验身份。", is_public=False)
        self.reset_actions(lambda p: p.role == Role.SEER)

    def process_action(self, action: ActionRequest) -> bool:
        player = self.find_player(action.player_id)
        if not player or player.role != Role.SEER:
            return False

        if action.type == ActionType.CHECK:
            if action.target_id is None:
                return False
            target = self.find_alive_player(action.target_id)
            if not target:
                return False

            is_good = target.role not in (Role.WOLF, Role.WOLF_KING)
            result_text = "好人" if is_good else "狼人"

            self.add_log(
                f"查验结果：{target.id}号是 {result_text}",
                player_id=player.id,
                is_public=False,
                data={"action": "seer_check", "target_id": target.id, "result": "good" if is_good else "bad"},
            )
            target.checked_by_seer = True
            player.has_acted = True
            return True

        if action.type == ActionType.PASS:
            player.has_acted = True
            return True

        return False

    def try_advance(self) -> GamePhase:
        seer = self.find_role_player(Role.SEER)
        if not seer or not seer.is_alive or seer.has_acted:
            return GamePhase.NIGHT_WITCH
        return None
