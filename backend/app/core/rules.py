from typing import List, Optional
from app.models.game_state import DeathCause, GameState, Role, Player

class Rules:
    @staticmethod
    def check_win_condition(game: GameState) -> Optional[str]:
        """
        Check if the game has ended.
        Returns: "wolf", "good", or None
        """
        alive_wolves = [p for p in game.players if p.is_alive and p.role in [Role.WOLF, Role.WOLF_KING]]
        alive_gods = [p for p in game.players if p.is_alive and p.role in [Role.SEER, Role.WITCH, Role.GUARD, Role.HUNTER]]
        alive_villagers = [p for p in game.players if p.is_alive and p.role == Role.VILLAGER]

        # Villager win: All wolves dead (check first to avoid false wolf win)
        if not alive_wolves:
            return "good"

        # Wolf win: Slaughter all gods OR all villagers (Side Slaughter rule)
        if not alive_gods or not alive_villagers:
            return "wolf"
            
        return None

    @staticmethod
    def resolve_night_deaths(game: GameState) -> List[int]:
        """
        Resolve deaths at the end of the night based on actions.
        Returns a list of player IDs who died.
        """
        deaths = set()
        
        for player in game.players:
            if not player.is_alive:
                continue
                
            is_killed = player.killed_by_wolf
            is_poisoned = player.poisoned_by_witch
            is_guarded = player.protected_by_guard
            is_saved = player.saved_by_witch
            
            # Rule: Saved and Guarded at the same time -> Dead (Milk + Guard = Dead)
            if is_saved and is_guarded and is_killed:
                deaths.add(player.id)
                continue
                
            # Rule: Guarded -> Safe from wolf kill
            if is_guarded and is_killed:
                is_killed = False
                
            # Rule: Saved -> Safe from wolf kill
            if is_saved and is_killed:
                is_killed = False
                
            # Final death check
            if is_killed or is_poisoned:
                deaths.add(player.id)
                
        return list(deaths)

    @staticmethod
    def can_shoot(
        player: Player,
        death_reason: str | DeathCause | None,
        alive_wolves: Optional[int] = None,
    ) -> bool:
        """
        Check if a player can shoot (Hunter or Wolf King).
        death_reason: "vote", "poison", "kill", "self_explode", or DeathCause value
        """
        if death_reason is None:
            cause = player.death_cause
        elif isinstance(death_reason, DeathCause):
            cause = death_reason
        else:
            mapping = {
                "vote": DeathCause.VOTE_EXILE,
                "kill": DeathCause.WOLF_KILL,
                "poison": DeathCause.WITCH_POISON,
                "self_explode": DeathCause.SELF_EXPLODE,
            }
            cause = mapping.get(death_reason, player.death_cause)

        if player.role == Role.HUNTER:
            # Hunter cannot shoot if poisoned
            return cause != DeathCause.WITCH_POISON
        if player.role == Role.WOLF_KING:
            # Wolf King cannot shoot if poisoned, self exploded, or was the last wolf.
            if cause in (DeathCause.WITCH_POISON, DeathCause.SELF_EXPLODE):
                return False
            if alive_wolves is not None and alive_wolves <= 0:
                return False
            return True
        return False
