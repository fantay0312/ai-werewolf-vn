from app.core.phase_handler import PhaseHandler
from app.models.game_state import GamePhase, ActionType
from app.models.action_model import ActionRequest


class SheriffTransferHandler(PhaseHandler):
    def get_phase(self) -> GamePhase:
        return GamePhase.SHERIFF_TRANSFER

    def on_enter(self):
        sheriff = next((p for p in self.game.players if p.is_sheriff), None)
        if sheriff and not sheriff.is_alive:
            eligible_recipient_ids = [
                player.id
                for player in self.game.players
                if player.is_alive and player.id != sheriff.id
            ]
            self.add_log(
                f"{sheriff.id}号玩家(警长)死亡，请移交警徽。",
                player_id=sheriff.id,
                log_type="action",
                data=self.build_event_data(
                    "sheriff_transfer_started",
                    sheriff_id=sheriff.id,
                    eligible_recipient_ids=eligible_recipient_ids,
                    next_phase=self._get_next_phase().value,
                ),
            )
            sheriff.has_acted = False

    def process_action(self, action: ActionRequest) -> bool:
        player = self.find_player(action.player_id)
        if not player or not player.is_sheriff:
            return False

        if action.type == ActionType.VOTE:
            target_id = action.target_id
            next_phase = self._get_next_phase().value
            if target_id == 0 or target_id is None:
                # Tear badge
                self.game.sheriff_id = None
                player.is_sheriff = False
                self.add_log(
                    f"{player.id}号撕掉了警徽。",
                    player_id=player.id,
                    log_type="action",
                    data=self.build_event_data(
                        "sheriff_badge_torn",
                        action="tear_badge",
                        sheriff_id=player.id,
                        previous_sheriff_id=player.id,
                        next_sheriff_id=None,
                        next_phase=next_phase,
                    ),
                )
            else:
                target = self.find_alive_player(target_id)
                if not target:
                    return False
                player.is_sheriff = False
                target.is_sheriff = True
                self.game.sheriff_id = target.id
                self.add_log(
                    f"{player.id}号将警徽移交给了{target.id}号。",
                    player_id=player.id,
                    log_type="action",
                    data=self.build_event_data(
                        "sheriff_badge_transferred",
                        action="transfer_badge",
                        sheriff_id=player.id,
                        previous_sheriff_id=player.id,
                        target_id=target.id,
                        next_sheriff_id=target.id,
                        next_phase=next_phase,
                    ),
                )

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
