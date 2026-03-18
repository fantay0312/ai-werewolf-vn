from app.core.phase_handler import PhaseHandler
from app.models.game_state import GamePhase, ActionType
from app.models.action_model import ActionRequest


class SheriffTransferHandler(PhaseHandler):
    def get_phase(self) -> GamePhase:
        return GamePhase.SHERIFF_TRANSFER

    def on_enter(self):
        sheriff = next((p for p in self.game.players if p.is_sheriff), None)
        if sheriff and not sheriff.is_alive:
            self.add_log(f"{sheriff.id}号玩家(警长)死亡，请移交警徽。")
            sheriff.has_acted = False

    def process_action(self, action: ActionRequest) -> bool:
        player = self.find_player(action.player_id)
        if not player or not player.is_sheriff:
            return False

        if action.type == ActionType.VOTE:
            target_id = action.target_id
            if target_id == 0 or target_id is None:
                # Tear badge
                self.game.sheriff_id = None
                player.is_sheriff = False
                self.add_log(f"{player.id}号撕掉了警徽。")
            else:
                target = self.find_alive_player(target_id)
                if not target:
                    return False
                player.is_sheriff = False
                target.is_sheriff = True
                self.game.sheriff_id = target.id
                self.add_log(f"{player.id}号将警徽移交给了{target.id}号。")

            player.has_acted = True
            return True

        return False

    def try_advance(self) -> GamePhase:
        sheriff = next((p for p in self.game.players if p.is_sheriff), None)

        if sheriff and sheriff.is_alive:
            return self._get_next_phase()
        if not sheriff:
            return self._get_next_phase()
        if not sheriff.has_acted:
            return None
        return self._get_next_phase()

    def _get_next_phase(self):
        if hasattr(self.game, 'next_phase_after_skill') and self.game.next_phase_after_skill:
            return self.game.next_phase_after_skill
        return GamePhase.DAY_DISCUSS
