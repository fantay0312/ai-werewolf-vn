from abc import abstractmethod
from typing import List, Optional

from app.core.phase_handler import PhaseHandler
from app.models.action_model import ActionRequest
from app.models.game_state import ActionType, GamePhase, Player


class TurnWindowHandler(PhaseHandler):
    """Common strict, one-speaker-at-a-time phase behavior."""

    speech_event: str
    turn_end_event: str

    def prime_speaking_window(self, order: List[int], participant_ids: Optional[List[int]] = None):
        self.game.speaking_order = list(order)
        self.game.current_speaker_index = 0
        active_ids = set(participant_ids if participant_ids is not None else order)
        for player in self.game.players:
            if player.id in active_ids:
                player.has_acted = True
        self.activate_current_speaker()

    def current_speaker_id(self) -> Optional[int]:
        if not self.game.speaking_order:
            return None
        if self.game.current_speaker_index >= len(self.game.speaking_order):
            return None
        return self.game.speaking_order[self.game.current_speaker_index]

    def activate_current_speaker(self) -> Optional[Player]:
        speaker_id = self.current_speaker_id()
        if speaker_id is None:
            return None
        player = self.find_player(speaker_id)
        if player:
            player.has_acted = False
        return player

    def advance_speaker(self):
        self.game.current_speaker_index += 1

    def advance_speaker_to_valid(self, valid_speaker_ids: Optional[List[int]] = None):
        self.advance_speaker()
        if valid_speaker_ids is None:
            return
        valid_ids = set(valid_speaker_ids)
        while (
            self.game.current_speaker_index < len(self.game.speaking_order)
            and self.game.speaking_order[self.game.current_speaker_index] not in valid_ids
        ):
            self.advance_speaker()

    def is_current_speaker(self, player_id: int) -> bool:
        return self.current_speaker_id() == player_id

    def all_speakers_done(self) -> bool:
        return self.game.current_speaker_index >= len(self.game.speaking_order)

    def process_action(self, action: ActionRequest) -> bool:
        player = self._current_turn_player(action.player_id)
        if not player:
            return False
        if action.type not in self._allowed_turn_actions():
            return False

        speaker_index = self.game.current_speaker_index
        next_speaker = self._complete_turn(player)
        is_speech = action.type == ActionType.SPEECH
        self.add_log(
            self._speech_content(player, action) if is_speech else self._turn_end_content(player),
            player_id=player.id,
            log_type="speech" if is_speech else "action",
            data=self.build_event_data(
                self.speech_event if is_speech else self.turn_end_event,
                action=action.type.value,
                speaker_id=player.id,
                speaker_index=speaker_index,
                **self._turn_event_fields(),
                next_speaker_id=next_speaker.id if next_speaker else None,
            ),
        )
        return True

    def try_advance(self) -> Optional[GamePhase]:
        if self.all_speakers_done():
            return self._on_window_finished()
        return None

    def _current_turn_player(self, player_id: int) -> Optional[Player]:
        if not self.is_current_speaker(player_id):
            return None
        player = self.find_player(player_id)
        return player if player and self._is_eligible_speaker(player) else None

    def _complete_turn(self, player: Player) -> Optional[Player]:
        player.has_acted = True
        self.advance_speaker_to_valid(self._valid_speaker_ids())
        return self.activate_current_speaker()

    def _valid_speaker_ids(self) -> Optional[List[int]]:
        return None

    def _allowed_turn_actions(self) -> set[ActionType]:
        return {ActionType.SPEECH, ActionType.CONFIRM, ActionType.PASS}

    def _is_eligible_speaker(self, player: Player) -> bool:
        return True

    def _turn_event_fields(self) -> dict:
        return {"speaking_order": list(self.game.speaking_order)}

    @abstractmethod
    def _speech_content(self, player: Player, action: ActionRequest) -> str:
        pass

    @abstractmethod
    def _turn_end_content(self, player: Player) -> str:
        pass

    @abstractmethod
    def _on_window_finished(self) -> GamePhase:
        pass
