import uuid
import logging
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Tuple
from app.core.rules import Rules
from app.models.game_state import DeathCause, GameState, GamePhase, GameLog, Player, Role
from app.models.action_model import ActionRequest

logger = logging.getLogger(__name__)


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

    # === Utility Methods ===

    def find_player(self, player_id: int) -> Optional[Player]:
        """Find a player by ID."""
        return next((p for p in self.game.players if p.id == player_id), None)

    def find_alive_player(self, player_id: int) -> Optional[Player]:
        """Find an alive player by ID. Returns None if not found or dead."""
        p = self.find_player(player_id)
        return p if p and p.is_alive else None

    def is_alive_target(self, target_id: Optional[int]) -> bool:
        """Return True when target_id points to an alive player."""
        return target_id is not None and self.find_alive_player(target_id) is not None

    def alive_wolf_count(self) -> int:
        """Get the number of alive wolves after current deaths are applied."""
        return len([
            p for p in self.game.players
            if p.is_alive and p.role in (Role.WOLF, Role.WOLF_KING)
        ])

    def add_log(self, content: str, *, player_id: Optional[int] = None,
                is_public: bool = True, log_type: str = "normal",
                data: Optional[Dict] = None) -> GameLog:
        """Create and append a GameLog entry."""
        log = GameLog(
            id=str(uuid.uuid4()),
            day=self.game.day,
            phase=self.game.phase,
            content=content,
            player_id=player_id,
            is_public=is_public,
            type=log_type,
            data=data,
        )
        self.game.game_logs.append(log)
        return log

    def build_event_data(self, event: str, **fields) -> Dict:
        """Build structured event data for replay and AI extraction."""
        data = {
            "event": event,
            "phase": self.game.phase.value,
            "day": self.game.day,
        }
        data.update(fields)
        return data

    def reset_actions(self, predicate=None):
        """Reset has_acted for players matching predicate. Defaults to all alive."""
        for p in self.game.players:
            if predicate is None:
                if p.is_alive:
                    p.has_acted = False
            elif predicate(p):
                p.has_acted = False

    def all_acted(self, predicate=None) -> bool:
        """Check if all players matching predicate have acted. Defaults to all alive."""
        for p in self.game.players:
            if predicate is None:
                if p.is_alive and not p.has_acted:
                    return False
            elif predicate(p) and not p.has_acted:
                return False
        return True

    def get_alive_players(self) -> List[Player]:
        """Get all alive players."""
        return [p for p in self.game.players if p.is_alive]

    def evaluate_win_condition(self) -> bool:
        """Update the winner after a death-producing resolution."""
        winner = Rules.check_win_condition(self.game)
        if winner is None:
            return False
        self.game.winner = winner
        return True

    def record_death(self, player: Player, cause: DeathCause) -> None:
        """Record immutable death facts at the resolution point."""
        player.is_alive = False
        player.death_cause = cause
        player.death_day = self.game.day
        player.death_phase = self.game.phase

    def get_wolves(self, alive_only: bool = True) -> List[Player]:
        """Get all wolf players (WOLF and WOLF_KING)."""
        return [
            p for p in self.game.players
            if p.role in (Role.WOLF, Role.WOLF_KING)
            and (not alive_only or p.is_alive)
        ]

    def find_role_player(self, role: Role) -> Optional[Player]:
        """Find the first player with the given role."""
        return next((p for p in self.game.players if p.role == role), None)

    def count_votes(self, votes: Dict[int, int], sheriff_weighted: bool = False) -> Dict[int, int]:
        """
        Count votes with optional sheriff weighting.
        Returns {target_id: total_votes} excluding abstentions (target_id=0).
        """
        vote_counts: Dict[int, int] = {}
        sheriff_id = self.game.sheriff_id if sheriff_weighted else None
        for voter_id, target_id in votes.items():
            if target_id == 0:
                continue
            weight = 2 if sheriff_id and voter_id == sheriff_id else 1
            vote_counts[target_id] = vote_counts.get(target_id, 0) + weight
        return vote_counts

    def format_vote_log(self, votes: Dict[int, int], prefix: str = "投票结果") -> str:
        """Format a vote log string with sheriff weight annotations."""
        sheriff_id = self.game.sheriff_id
        lines = [f"{prefix}：\n"]
        for voter_id, target_id in sorted(votes.items()):
            weight_str = "(警长票x2)" if voter_id == sheriff_id else ""
            target_name = f"{target_id}号" if target_id != 0 else "弃票"
            lines.append(f"{voter_id}号{weight_str} -> {target_name}\n")
        return "".join(lines)

    def resolve_vote_winner(self, vote_counts: Dict[int, int]) -> Tuple[Optional[int], int, List[int]]:
        """
        Resolve the winner from vote counts.
        Returns (winner_id_or_None, max_votes, tied_candidates).
        """
        if not vote_counts:
            return None, 0, []
        max_votes = max(vote_counts.values())
        candidates = [pid for pid, c in vote_counts.items() if c == max_votes]
        if len(candidates) == 1:
            return candidates[0], max_votes, candidates
        return None, max_votes, candidates

    def check_death_skills(self, dead_player_id: int, return_phase: GamePhase) -> Optional[GamePhase]:
        """
        Check if a dead player triggers death skills (Hunter/Wolf King shoot, Sheriff transfer).
        Sets next_phase_after_skill and returns the skill phase, or None.
        """
        from app.core.rules import Rules

        player = self.find_player(dead_player_id)
        if not player:
            return None

        # Check Hunter/Wolf King shooting
        if player.role in (Role.HUNTER, Role.WOLF_KING):
            if Rules.can_shoot(player, player.death_cause, alive_wolves=self.alive_wolf_count()):
                self.game.next_phase_after_skill = return_phase
                return GamePhase.HUNTER_SKILL

        # Check Sheriff transfer
        if player.is_sheriff:
            self.game.next_phase_after_skill = return_phase
            return GamePhase.SHERIFF_TRANSFER

        return None
