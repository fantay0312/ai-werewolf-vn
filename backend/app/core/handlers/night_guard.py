from app.core.phase_handler import PhaseHandler
from app.models.game_state import GamePhase, ActionType, Role
from app.models.action_model import ActionRequest


class NightGuardHandler(PhaseHandler):
    def get_phase(self) -> GamePhase:
        return GamePhase.NIGHT_GUARD

    def on_enter(self):
        guard = self.find_role_player(Role.GUARD)
        blocked_target_id = self.game.last_guarded_player
        allowed_target_ids = [
            player.id
            for player in self.game.players
            if player.is_alive and player.id != blocked_target_id
        ]
        self.add_log(
            "守卫请守护。",
            player_id=guard.id if guard else None,
            is_public=False,
            log_type="action",
            data=self.build_event_data(
                "guard_prompted",
                action="prompt",
                guard_id=guard.id if guard else None,
                guard_alive=bool(guard and guard.is_alive),
                blocked_target_id=blocked_target_id,
                allowed_target_ids=allowed_target_ids,
                next_phase_hint=GamePhase.NIGHT_RESOLVE.value,
            ),
        )
        self.reset_actions(lambda p: p.role == Role.GUARD)

    def process_action(self, action: ActionRequest) -> bool:
        player = self.find_player(action.player_id)
        if not player or player.role != Role.GUARD:
            return False

        if action.type == ActionType.GUARD:
            last_guarded_before = self.game.last_guarded_player
            if not self.is_alive_target(action.target_id):
                return False
            if self.game.last_guarded_player == action.target_id:
                return False
            target = self.find_alive_player(action.target_id)
            target.protected_by_guard = True
            self.game.last_guarded_player = action.target_id
            player.has_acted = True
            self.add_log(
                f"守卫守护了 {target.id} 号",
                player_id=player.id,
                is_public=False,
                log_type="action",
                data=self.build_event_data(
                    "guard_protected",
                    action="guard_protect",
                    actor_id=player.id,
                    target_id=target.id,
                    target_valid=True,
                    target_alive=True,
                    blocked_target_id_before=last_guarded_before,
                    blocked_target_id_after=self.game.last_guarded_player,
                    next_phase_hint=GamePhase.NIGHT_RESOLVE.value,
                ),
            )
            return True

        if action.type == ActionType.PASS:
            player.has_acted = True
            blocked_target_before = self.game.last_guarded_player
            self.game.last_guarded_player = None
            self.add_log(
                "守卫选择今晚不守护任何玩家。",
                player_id=player.id,
                is_public=False,
                log_type="action",
                data=self.build_event_data(
                    "guard_passed",
                    action="pass",
                    actor_id=player.id,
                    blocked_target_id_before=blocked_target_before,
                    blocked_target_id_after=self.game.last_guarded_player,
                    next_phase_hint=GamePhase.NIGHT_RESOLVE.value,
                ),
            )
            return True

        return False

    def try_advance(self) -> GamePhase:
        guard = self.find_role_player(Role.GUARD)
        if not guard or not guard.is_alive or guard.has_acted:
            return GamePhase.NIGHT_RESOLVE
        return None
