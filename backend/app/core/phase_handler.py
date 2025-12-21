from abc import ABC, abstractmethod
from typing import Optional
from app.models.game_state import GameState, GamePhase, ActionType
from app.models.action_model import ActionRequest

class PhaseHandler(ABC):
    def __init__(self, game_manager, game: GameState):
        self.gm = game_manager
        self.game = game

    @abstractmethod
    def get_phase(self) -> GamePhase:
        """Return the phase this handler is responsible for."""
        pass

    @abstractmethod
    def on_enter(self):
        """Called when the game enters this phase."""
        pass

    @abstractmethod
    def process_action(self, action: ActionRequest) -> bool:
        """
        Process a player action.
        Returns True if the action was valid and processed.
        """
        pass

    @abstractmethod
    def try_advance(self) -> Optional[GamePhase]:
        """
        Check if the phase should end and return the next phase.
        Returns None if the phase should continue.
        """
        pass
