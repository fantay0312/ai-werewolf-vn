from app.core.phase_handler import PhaseHandler
from app.models.game_state import GamePhase, ActionType, Role
from app.models.action_model import ActionRequest


class NightGuardHandler(PhaseHandler):
    def get_phase(self) -> GamePhase:
        return GamePhase.NIGHT_GUARD

    def on_enter(self):
        self.add_log("守卫请守护。", is_public=False)
        self.reset_actions(lambda p: p.role == Role.GUARD)

    def process_action(self, action: ActionRequest) -> bool:
        player = self.find_player(action.player_id)
        if not player or player.role != Role.GUARD:
            return False

        if action.type == ActionType.GUARD:
            if action.target_id is None:
                return False
            if self.game.last_guarded_player == action.target_id:
                return False
            target = self.find_player(action.target_id)
            if not target:
                return False
            target.protected_by_guard = True
            self.game.last_guarded_player = action.target_id
            player.has_acted = True
            self.add_log(
                f"守卫守护了 {target.id} 号",
                player_id=player.id, is_public=False,
                data={"action": "guard_protect", "target_id": target.id},
            )
            return True

        if action.type == ActionType.PASS:
            player.has_acted = True
            self.game.last_guarded_player = None
            return True

        return False

    def try_advance(self) -> GamePhase:
        guard = self.find_role_player(Role.GUARD)
        if not guard or not guard.is_alive or guard.has_acted:
            return GamePhase.NIGHT_RESOLVE
        return None
