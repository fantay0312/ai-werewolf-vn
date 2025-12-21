import pytest
from app.ai.hallucination_detector import HallucinationDetector
from app.ai.memory.fact_layer import FactLayer, SkillStatus
from app.models.game_state import GameState, GamePhase, Role, Player
from app.ai.prompt_builder import prompt_builder

def test_hallucination_detector():
    detector = HallucinationDetector()
    
    # Mock FactLayer
    fact_layer = FactLayer(
        game_id="test",
        current_day=1,
        current_phase=GamePhase.DAY_DISCUSS,
        my_player_id=1,
        my_role=Role.VILLAGER,
        my_camp="good",
        alive_players=[1, 2, 3],
        skill_status=SkillStatus()
    )
    
    # Mock GameState
    game_state = GameState(
        session_id="test",
        day=1,
        phase=GamePhase.DAY_DISCUSS,
        players=[]
    )
    
    # 1. Valid JSON
    valid_response = '{"thinking": "...", "action": {"type": "speech", "content": "hello"}}'
    result = detector.detect(valid_response, fact_layer, game_state)
    assert not result.has_hallucination
    
    # 2. Invalid JSON
    invalid_json = '{thinking: ...}'
    result = detector.detect(invalid_json, fact_layer, game_state)
    assert result.has_hallucination
    assert "Invalid JSON format" in result.issues
    
    # 3. Invalid Target (Dead)
    fact_layer.alive_players = [1, 2]
    invalid_target = '{"thinking": "...", "action": {"type": "vote", "target": 3}}'
    result = detector.detect(invalid_target, fact_layer, game_state)
    # Note: Detector currently checks target in alive_players. 3 is not alive.
    # But wait, target validation logic in detector:
    # if target is not None: ... if target not in fact_layer.alive_players ...
    # So it should fail.
    # However, vote action might allow voting for dead? No, usually vote for alive.
    # Let's check logic.
    # Logic: if target is not None: if target not in alive_players and target != 0: issue
    assert result.has_hallucination
    
    # 4. Permission Check (Villager trying to Seer check)
    invalid_action = '{"thinking": "...", "action": {"type": "seer_check", "target": 2}}'
    result = detector.detect(invalid_action, fact_layer, game_state)
    assert result.has_hallucination
    assert any("cannot perform seer_check" in issue for issue in result.issues)

def test_prompt_builder():
    fact_layer = FactLayer(
        game_id="test",
        current_day=1,
        current_phase=GamePhase.NIGHT_SEER,
        my_player_id=1,
        my_role=Role.SEER,
        my_camp="good",
        alive_players=[1, 2, 3],
        skill_status=SkillStatus()
    )
    
    prompt = prompt_builder.build_current_task_block(fact_layer)
    assert "seer_check" in prompt
    assert "可选行动" in prompt
    
    fact_layer.current_phase = GamePhase.NIGHT_WOLF_VOTE
    prompt = prompt_builder.build_current_task_block(fact_layer)
    assert "wolf_kill" in prompt

if __name__ == "__main__":
    # Manually run if pytest not available
    try:
        test_hallucination_detector()
        test_prompt_builder()
        print("All tests passed!")
    except AssertionError as e:
        print(f"Test failed: {e}")
    except Exception as e:
        print(f"Error: {e}")
