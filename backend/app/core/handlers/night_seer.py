from app.core.phase_handler import PhaseHandler
from app.models.game_state import GamePhase, ActionType, Role
from app.models.action_model import ActionRequest


class NightSeerHandler(PhaseHandler):
    def get_phase(self) -> GamePhase:
        return GamePhase.NIGHT_SEER

    def on_enter(self):
        seer = self.find_role_player(Role.SEER)
        allowed_target_ids = [p.id for p in self.game.players if p.is_alive]
        self.add_log(
            "预言家请查验身份。",
            player_id=seer.id if seer else None,
            is_public=False,
            log_type="action",
            data=self.build_event_data(
                "seer_prompted",
                action="prompt",
                seer_id=seer.id if seer else None,
                seer_alive=bool(seer and seer.is_alive),
                allowed_target_ids=allowed_target_ids,
                next_phase_hint=GamePhase.NIGHT_WITCH.value,
            ),
        )
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
                log_type="action",
                data=self.build_event_data(
                    "seer_checked",
                    action="seer_check",
                    actor_id=player.id,
                    target_id=target.id,
                    target_valid=True,
                    target_alive=True,
                    result="good" if is_good else "bad",
                    result_text=result_text,
                    next_phase_hint=GamePhase.NIGHT_WITCH.value,
                ),
            )
            target.checked_by_seer = True
            player.has_acted = True
            return True

        if action.type == ActionType.PASS:
            player.has_acted = True
            self.add_log(
                "预言家选择今晚不查验。",
                player_id=player.id,
                is_public=False,
                log_type="action",
                data=self.build_event_data(
                    "seer_passed",
                    action="pass",
                    actor_id=player.id,
                    next_phase_hint=GamePhase.NIGHT_WITCH.value,
                ),
            )
            return True

        return False

    def try_advance(self) -> GamePhase:
        seer = self.find_role_player(Role.SEER)
        if not seer or not seer.is_alive or seer.has_acted:
            return GamePhase.NIGHT_WITCH
        return None
