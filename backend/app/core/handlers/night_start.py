from app.core.phase_handler import PhaseHandler
from app.models.game_state import GamePhase
from app.models.action_model import ActionRequest


class NightStartHandler(PhaseHandler):
    def get_phase(self) -> GamePhase:
        return GamePhase.NIGHT_START

    def on_enter(self):
        alive_player_ids = [player.id for player in self.game.players if player.is_alive]
        dead_player_ids = [player.id for player in self.game.players if not player.is_alive]

        # Reset nightly states
        self.game.wolf_kill_target = None
        self.game.votes = {}
        self.game.wolf_discuss_messages = []
        for p in self.game.players:
            p.has_acted = False
            p.protected_by_guard = False
            p.killed_by_wolf = False
            p.poisoned_by_witch = False
            p.saved_by_witch = False
            p.checked_by_seer = False

        self.add_log(
            f"第{self.game.day}夜，天黑请闭眼。",
            data=self.build_event_data(
                "night_started",
                night_number=self.game.day,
                alive_player_ids=alive_player_ids,
                alive_player_count=len(alive_player_ids),
                dead_player_ids=dead_player_ids,
                dead_player_count=len(dead_player_ids),
                sheriff_id=self.game.sheriff_id,
                wolf_kill_target=self.game.wolf_kill_target,
                votes=dict(self.game.votes),
                wolf_discuss_message_count=len(self.game.wolf_discuss_messages),
                reset_fields=[
                    "wolf_kill_target",
                    "votes",
                    "wolf_discuss_messages",
                    "has_acted",
                    "protected_by_guard",
                    "killed_by_wolf",
                    "poisoned_by_witch",
                    "saved_by_witch",
                    "checked_by_seer",
                ],
                next_phase_hint=GamePhase.NIGHT_WOLF_DISCUSS.value,
            ),
        )

    def process_action(self, action: ActionRequest) -> bool:
        return False

    def try_advance(self) -> GamePhase:
        return GamePhase.NIGHT_WOLF_DISCUSS
