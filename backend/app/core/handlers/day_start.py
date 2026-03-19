from app.core.phase_handler import PhaseHandler
from app.models.game_state import GamePhase, ActionType
from app.models.action_model import ActionRequest
from app.core.rules import Rules


class DayStartHandler(PhaseHandler):
    def get_phase(self) -> GamePhase:
        return GamePhase.DAY_START

    def on_enter(self):
        dead_ids = self.game.dead_players
        if not dead_ids:
            content = "天亮了。昨晚是平安夜。"
        else:
            dead_str = ", ".join([f"{pid}号" for pid in dead_ids])
            content = f"天亮了。昨晚死亡的是 {dead_str}。"

        winner = Rules.check_win_condition(self.game)
        if winner:
            self.game.winner = winner

        self.add_log(
            content,
            data=self.build_event_data(
                "day_started",
                day_number=self.game.day,
                dead_player_ids=list(dead_ids),
                dead_player_count=len(dead_ids),
                is_peaceful_night=not dead_ids,
                sheriff_id=self.game.sheriff_id,
                pending_sheriff_election=self.game.pending_sheriff_election,
                election_cancelled=self.game.election_cancelled,
                winner=self.game.winner,
                next_phase_hint=self._next_phase_hint(),
            ),
        )

    def process_action(self, action: ActionRequest) -> bool:
        if action.type in (ActionType.CONFIRM, ActionType.PASS):
            player = self.find_player(action.player_id)
            if player:
                player.has_acted = True
                acted_player_ids = sorted(candidate.id for candidate in self.game.players if candidate.has_acted)
                self.add_log(
                    f"{player.id}号玩家确认进入白天流程。",
                    player_id=player.id,
                    log_type="action",
                    data=self.build_event_data(
                        "day_start_acknowledged",
                        action=action.type.value,
                        player_id=player.id,
                        winner=self.game.winner,
                        dead_player_ids=list(self.game.dead_players),
                        pending_sheriff_election=self.game.pending_sheriff_election,
                        election_cancelled=self.game.election_cancelled,
                        acted_player_ids=acted_player_ids,
                        acted_count=len(acted_player_ids),
                        advance_condition="any_confirm",
                        next_phase_hint=self._next_phase_hint(),
                    ),
                )
                return True
        return False

    def try_advance(self) -> GamePhase:
        if self.game.winner:
            return GamePhase.GAME_END

        if self.game.day == 1 and self.game.dead_players:
            return GamePhase.DAY_LAST_WORDS

        if self.game.election_cancelled:
            return GamePhase.DAY_DISCUSS

        if self.game.day == 1 or self.game.pending_sheriff_election:
            if self.game.pending_sheriff_election:
                self.game.pending_sheriff_election = False
            return GamePhase.SHERIFF_ELECTION

        return GamePhase.DAY_DISCUSS

    def _next_phase_hint(self) -> str:
        if self.game.winner:
            return GamePhase.GAME_END.value
        if self.game.day == 1 and self.game.dead_players:
            return GamePhase.DAY_LAST_WORDS.value
        if self.game.election_cancelled:
            return GamePhase.DAY_DISCUSS.value
        if self.game.day == 1 or self.game.pending_sheriff_election:
            return GamePhase.SHERIFF_ELECTION.value
        return GamePhase.DAY_DISCUSS.value
