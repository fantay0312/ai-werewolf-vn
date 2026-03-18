from app.core.phase_handler import PhaseHandler
from app.models.game_state import GamePhase, ActionType, Role
from app.models.action_model import ActionRequest


class HunterSkillHandler(PhaseHandler):
    def get_phase(self) -> GamePhase:
        return GamePhase.HUNTER_SKILL

    def on_enter(self):
        shooter = self._find_shooter()
        if shooter:
            role_name = "猎人" if shooter.role == Role.HUNTER else "狼王"
            self.add_log(f"{shooter.id}号玩家({role_name})死亡，请选择是否发动技能开枪带人。")
            shooter.has_acted = False

    def process_action(self, action: ActionRequest) -> bool:
        player = self.find_player(action.player_id)
        if not player:
            return False

        shooter = self._find_shooter()
        if not shooter or player.id != shooter.id:
            return False

        if action.type == ActionType.SHOOT:
            target = self.find_alive_player(action.target_id)
            if not target:
                return False
            target.is_alive = False
            self.game.dead_players.append(target.id)
            player.gun_used = True
            player.has_acted = True
            self.add_log(f"{player.id}号玩家开枪带走了{target.id}号玩家。")
            return True

        if action.type == ActionType.PASS:
            player.gun_used = True
            player.has_acted = True
            self.add_log(f"{player.id}号玩家选择不开枪。")
            return True

        return False

    def try_advance(self) -> GamePhase:
        shooter = self._find_shooter()
        if shooter:
            return None

        # Check for Sheriff Transfer
        dead_sheriff = next(
            (p for p in self.game.players if not p.is_alive and p.is_sheriff), None
        )
        if dead_sheriff:
            return GamePhase.SHERIFF_TRANSFER

        if hasattr(self.game, 'next_phase_after_skill') and self.game.next_phase_after_skill:
            return self.game.next_phase_after_skill

        return GamePhase.DAY_DISCUSS

    def _find_shooter(self):
        for p in self.game.players:
            if (not p.is_alive
                    and p.role in (Role.HUNTER, Role.WOLF_KING)
                    and not p.gun_used
                    and not p.poisoned_by_witch):
                return p
        return None
