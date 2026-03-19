from app.core.phase_handler import PhaseHandler
from app.models.game_state import GamePhase, ActionType, Role
from app.models.action_model import ActionRequest


class NightWitchHandler(PhaseHandler):
    def get_phase(self) -> GamePhase:
        return GamePhase.NIGHT_WITCH

    def on_enter(self):
        witch = self.find_role_player(Role.WITCH)
        content = "女巫请行动。"
        killed_id = self.game.wolf_kill_target

        if witch and witch.is_alive and not witch.antidote_used:
            if killed_id:
                content += f" 今晚 {killed_id} 号被杀了。"
            else:
                content += " 今晚平安夜。"

        allowed_poison_targets = [
            player.id for player in self.game.players if player.is_alive
        ]
        allowed_save_target = (
            killed_id
            if witch and witch.is_alive and not witch.antidote_used and killed_id
            else None
        )

        self.add_log(
            content,
            player_id=witch.id if witch else None,
            is_public=False,
            log_type="action",
            data=self.build_event_data(
                "witch_prompted",
                action="prompt",
                witch_id=witch.id if witch else None,
                witch_alive=bool(witch and witch.is_alive),
                wolf_kill_target=killed_id,
                can_save_target_id=allowed_save_target,
                allowed_poison_target_ids=allowed_poison_targets,
                antidote_available=bool(witch and not witch.antidote_used),
                poison_available=bool(witch and not witch.poison_used),
                next_phase_hint=GamePhase.NIGHT_GUARD.value,
            ),
        )

        if witch:
            witch.has_acted = False

    def process_action(self, action: ActionRequest) -> bool:
        player = self.find_player(action.player_id)
        if not player or player.role != Role.WITCH:
            return False

        if action.type == ActionType.SAVE:
            if player.antidote_used:
                return False
            target_id = self.game.wolf_kill_target
            if not target_id:
                return False
            target = self.find_player(target_id)
            if not target:
                return False
            target.saved_by_witch = True
            player.antidote_used = True
            player.has_acted = True
            self.add_log(
                f"女巫使用解药救了 {target.id} 号",
                player_id=player.id,
                is_public=False,
                log_type="action",
                data=self.build_event_data(
                    "witch_saved",
                    action="witch_save",
                    actor_id=player.id,
                    target_id=target.id,
                    target_valid=True,
                    target_alive=target.is_alive,
                    target_source="wolf_kill_target",
                    wolf_kill_target=self.game.wolf_kill_target,
                    antidote_available_before=True,
                    antidote_available_after=False,
                    poison_available_after=not player.poison_used,
                    next_phase_hint=GamePhase.NIGHT_GUARD.value,
                ),
            )
            return True

        if action.type == ActionType.POISON:
            if player.poison_used or action.target_id is None:
                return False
            target = self.find_alive_player(action.target_id)
            if not target:
                return False
            target.poisoned_by_witch = True
            player.poison_used = True
            player.has_acted = True
            self.add_log(
                f"女巫使用毒药毒了 {target.id} 号",
                player_id=player.id,
                is_public=False,
                log_type="action",
                data=self.build_event_data(
                    "witch_poisoned",
                    action="witch_poison",
                    actor_id=player.id,
                    target_id=target.id,
                    target_valid=True,
                    target_alive=True,
                    antidote_available_after=not player.antidote_used,
                    poison_available_before=True,
                    poison_available_after=False,
                    next_phase_hint=GamePhase.NIGHT_GUARD.value,
                ),
            )
            return True

        if action.type == ActionType.PASS:
            player.has_acted = True
            self.add_log(
                "女巫选择今晚不使用药品。",
                player_id=player.id,
                is_public=False,
                log_type="action",
                data=self.build_event_data(
                    "witch_passed",
                    action="pass",
                    actor_id=player.id,
                    wolf_kill_target=self.game.wolf_kill_target,
                    can_save_target_id=(
                        self.game.wolf_kill_target
                        if not player.antidote_used and self.game.wolf_kill_target
                        else None
                    ),
                    antidote_available=not player.antidote_used,
                    poison_available=not player.poison_used,
                    next_phase_hint=GamePhase.NIGHT_GUARD.value,
                ),
            )
            return True

        return False

    def try_advance(self) -> GamePhase:
        witch = self.find_role_player(Role.WITCH)
        if not witch or not witch.is_alive or witch.has_acted:
            return GamePhase.NIGHT_GUARD
        return None
