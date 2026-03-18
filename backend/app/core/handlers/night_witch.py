from app.core.phase_handler import PhaseHandler
from app.models.game_state import GamePhase, ActionType, Role
from app.models.action_model import ActionRequest


class NightWitchHandler(PhaseHandler):
    def get_phase(self) -> GamePhase:
        return GamePhase.NIGHT_WITCH

    def on_enter(self):
        witch = self.find_role_player(Role.WITCH)
        content = "女巫请行动。"

        if witch and witch.is_alive and not witch.antidote_used:
            killed_id = self.game.wolf_kill_target
            if killed_id:
                content += f" 今晚 {killed_id} 号被杀了。"
            else:
                content += " 今晚平安夜。"

        self.add_log(content, player_id=witch.id if witch else None, is_public=False)

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
                player_id=player.id, is_public=False,
                data={"action": "witch_save", "target_id": target.id},
            )
            return True

        if action.type == ActionType.POISON:
            if player.poison_used or action.target_id is None:
                return False
            target = self.find_player(action.target_id)
            if not target:
                return False
            target.poisoned_by_witch = True
            player.poison_used = True
            player.has_acted = True
            self.add_log(
                f"女巫使用毒药毒了 {target.id} 号",
                player_id=player.id, is_public=False,
                data={"action": "witch_poison", "target_id": target.id},
            )
            return True

        if action.type == ActionType.PASS:
            player.has_acted = True
            return True

        return False

    def try_advance(self) -> GamePhase:
        witch = self.find_role_player(Role.WITCH)
        if not witch or not witch.is_alive or witch.has_acted:
            return GamePhase.NIGHT_GUARD
        return None
