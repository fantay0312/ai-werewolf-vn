import pytest
import uuid
from app.core.handlers.night_witch import NightWitchHandler
from app.core.handlers.night_guard import NightGuardHandler
from app.models.game_state import GameState, GamePhase, Player, Role, ActionType
from app.models.action_model import ActionRequest

def test_witch_logging():
    # Setup GameState
    witch = Player(id=1, name="Witch", role=Role.WITCH, portrait="")
    game = GameState(
        session_id="test",
        day=1,
        phase=GamePhase.NIGHT_WITCH,
        players=[witch],
        wolf_kill_target=2
    )
    handler = NightWitchHandler(None, game) # GameManager not needed for this test
    
    # Test SAVE
    action = ActionRequest(player_id=1, type=ActionType.SAVE, timestamp=0)
    # Need a target player in game
    victim = Player(id=2, name="Victim", role=Role.VILLAGER, portrait="")
    game.players.append(victim)
    
    handler.process_action(action)
    
    log = game.game_logs[-1]
    assert log.data is not None
    assert log.data["action"] == "witch_save"
    assert log.data["target_id"] == 2

def test_guard_logging():
    # Setup GameState
    guard = Player(id=1, name="Guard", role=Role.GUARD, portrait="")
    target = Player(id=2, name="Target", role=Role.VILLAGER, portrait="")
    game = GameState(
        session_id="test",
        day=1,
        phase=GamePhase.NIGHT_GUARD,
        players=[guard, target]
    )
    handler = NightGuardHandler(None, game)
    
    # Test GUARD
    action = ActionRequest(player_id=1, type=ActionType.GUARD, target_id=2, timestamp=0)
    handler.process_action(action)
    
    log = game.game_logs[-1]
    assert log.data is not None
    assert log.data["action"] == "guard_protect"
    assert log.data["target_id"] == 2

if __name__ == "__main__":
    try:
        test_witch_logging()
        test_guard_logging()
        print("All logging tests passed!")
    except AssertionError as e:
        print(f"Test failed: {e}")
    except Exception as e:
        print(f"Error: {e}")
