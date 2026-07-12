import pytest
import uuid
from app.ai.memory.memory_manager import MemoryManager
from app.models.game_state import GameState, GamePhase, Player, Role, GameLog
from app.ai.memory.fact_layer import ConfirmedAction
from app.ai.memory.recent_layer import DialogueEntry
from app.application.ai.memory_lifecycle import MemoryLifecycleManager

def test_memory_manager_confirmed_actions():
    # Setup
    player = Player(id=1, name="TestPlayer", role=Role.VILLAGER, portrait="")
    manager = MemoryManager(player)
    
    # Create logs with structured actions
    log1 = GameLog(
        id=str(uuid.uuid4()),
        day=1,
        phase=GamePhase.NIGHT_SEER,
        content="Seer check",
        player_id=2, # Another player
        is_public=False,
        data={"action": "seer_check", "target_id": 3, "result": "good"}
    )
    # Public action
    log2 = GameLog(
        id=str(uuid.uuid4()),
        day=1,
        phase=GamePhase.DAY_VOTE,
        content="Vote",
        player_id=3,
        is_public=True,
        data={"action": "vote", "target_id": 4}
    )
    
    game = GameState(
        session_id="test",
        day=1,
        phase=GamePhase.DAY_DISCUSS,
        players=[
            player, 
            Player(id=2, name="Seer", role=Role.SEER, portrait=""), 
            Player(id=3, name="Villager", role=Role.VILLAGER, portrait="")
        ],
        game_logs=[log1, log2]
    )
    
    # Update facts
    manager.update_facts(game)
    
    # Verify confirmed_actions
    # log1 is private and not mine, should NOT be in confirmed_actions
    # log2 is public, SHOULD be in confirmed_actions
    
    assert len(manager.fact_layer.confirmed_actions) == 1
    action = manager.fact_layer.confirmed_actions[0]
    assert action.action_type == "vote"
    assert action.actor_id == 3
    assert action.target_id == 4

def test_memory_manager_recent_dialogue():
    # Setup
    player = Player(id=1, name="TestPlayer", role=Role.VILLAGER, portrait="")
    manager = MemoryManager(player)
    
    # Create dialogue logs
    log1 = GameLog(
        id=str(uuid.uuid4()),
        day=1,
        phase=GamePhase.DAY_DISCUSS,
        content="Hello everyone",
        player_id=2,
        is_public=True
    )
    # Private wolf chat (should not be seen by Villager)
    log2 = GameLog(
        id=str(uuid.uuid4()),
        day=1,
        phase=GamePhase.NIGHT_WOLF_DISCUSS,
        content="Kill 3",
        player_id=4,
        is_public=False
    )
    
    game = GameState(
        session_id="test",
        day=1,
        phase=GamePhase.DAY_DISCUSS,
        players=[
            player, 
            Player(id=2, name="Speaker", role=Role.VILLAGER, portrait="")
        ],
        game_logs=[log1, log2]
    )
    
    # Process logs
    manager.update_facts(game) # This calls _process_new_logs
    
    # Verify recent layer
    # Should contain log1, but not log2
    assert len(manager.recent_layer.current_phase_dialogue) == 1
    entry = manager.recent_layer.current_phase_dialogue[0]
    assert entry.speaker_id == 2
    assert entry.content == "Hello everyone"


def test_memory_save_preserves_runtime_meta_and_unknown_keys():
    player = Player(
        id=1,
        name="MemoryOwner",
        role=Role.VILLAGER,
        portrait="",
        ai_memory={
            "_runtime_meta": {"last_seen_day": 2, "last_seen_phase": GamePhase.DAY_DISCUSS.value},
            "extension_payload": {"keep": True},
        },
    )
    manager = MemoryManager(player)

    manager.save_to_player(player)

    assert player.ai_memory["_runtime_meta"] == {
        "last_seen_day": 2,
        "last_seen_phase": GamePhase.DAY_DISCUSS.value,
    }
    assert player.ai_memory["extension_payload"] == {"keep": True}
    next_game = GameState(
        session_id="memory-rollover",
        day=2,
        phase=GamePhase.DAY_VOTE,
        players=[player],
    )
    plan = MemoryLifecycleManager().build_plan_from_player(player, next_game)
    assert plan.transition.phase_changed is True

if __name__ == "__main__":
    try:
        test_memory_manager_confirmed_actions()
        test_memory_manager_recent_dialogue()
        print("All memory manager tests passed!")
    except AssertionError as e:
        print(f"Test failed: {e}")
    except Exception as e:
        print(f"Error: {e}")
