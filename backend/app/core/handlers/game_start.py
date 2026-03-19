from app.core.phase_handler import PhaseHandler
from app.models.game_state import GamePhase, ActionType
from app.models.action_model import ActionRequest


class GameStartHandler(PhaseHandler):
    def get_phase(self) -> GamePhase:
        return GamePhase.GAME_START

    def on_enter(self):
        participant_ids = [player.id for player in self.game.players]
        human_player = next((player for player in self.game.players if player.is_human), None)
        self.add_log(
            "游戏开始！请确认您的身份。",
            data=self.build_event_data(
                "game_start_prompt",
                participant_ids=participant_ids,
                participant_count=len(participant_ids),
                human_player_id=human_player.id if human_player else None,
                required_action=ActionType.CONFIRM.value,
                accepted_actions=[ActionType.CONFIRM.value, ActionType.PASS.value],
                advance_condition="human_confirmed",
                next_phase_hint=GamePhase.SHERIFF_ELECTION.value,
            ),
        )
        self.reset_actions()

    def process_action(self, action: ActionRequest) -> bool:
        if action.type in (ActionType.CONFIRM, ActionType.PASS):
            player = self.find_player(action.player_id)
            if player:
                player.has_acted = True
                human = next((candidate for candidate in self.game.players if candidate.is_human), None)
                acted_player_ids = sorted(candidate.id for candidate in self.game.players if candidate.has_acted)
                pending_player_ids = sorted(candidate.id for candidate in self.game.players if not candidate.has_acted)
                self.add_log(
                    f"{player.id}号玩家已确认开始游戏。",
                    player_id=player.id,
                    is_public=False,
                    log_type="action",
                    data=self.build_event_data(
                        "game_start_acknowledged",
                        action=action.type.value,
                        player_id=player.id,
                        is_human=player.is_human,
                        human_player_id=human.id if human else None,
                        human_confirmed=bool(human and human.has_acted),
                        acted_player_ids=acted_player_ids,
                        pending_player_ids=pending_player_ids,
                        acted_count=len(acted_player_ids),
                        pending_count=len(pending_player_ids),
                        advance_condition_met=bool(human and human.has_acted),
                        next_phase_hint=GamePhase.SHERIFF_ELECTION.value if human and human.has_acted else None,
                    ),
                )
                return True
        return False

    def try_advance(self) -> GamePhase:
        human = next((p for p in self.game.players if p.is_human), None)
        if human and human.has_acted:
            return GamePhase.SHERIFF_ELECTION
        return None
