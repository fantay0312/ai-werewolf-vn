import pytest
from app.core.game_manager import GameManager
from app.models.game_state import GamePhase, Role, ActionType
from app.models.action_model import ActionRequest
from app.core.handlers.day_last_words import DayLastWordsHandler
from app.core.handlers.sheriff_speech import SheriffSpeechHandler
from app.core.handlers.day_vote_result import DayVoteResultHandler

def test_day_last_words_handler():
    gm = GameManager()
    game = gm.create_game()
    game.day = 1
    game.phase = GamePhase.DAY_LAST_WORDS
    game.dead_players = [1] # Player 1 died
    
    handler = DayLastWordsHandler(gm, game)
    handler.on_enter()
    
    assert game.phase == GamePhase.DAY_LAST_WORDS
    assert game.speaking_order == [1]
    
    # Player 1 speaks
    action = ActionRequest(player_id=1, type=ActionType.SPEECH, content="Last words", timestamp=0)
    assert handler.process_action(action) is True
    
    # Advance
    assert handler.try_advance() == GamePhase.SHERIFF_ELECTION

def test_sheriff_vote_weight():
    gm = GameManager()
    game = gm.create_game()
    game.sheriff_id = 1
    game.players[0].is_sheriff = True # Player 1 (index 0) is sheriff
    
    # Votes: 1(Sheriff) -> 2, 3 -> 2, 4 -> 5
    game.votes = {1: 2, 3: 2, 4: 5}
    
    handler = DayVoteResultHandler(gm, game)
    handler.on_enter()
    
    # Check logs for vote counts
    # Player 2 should have 2(Sheriff) + 1 = 3 votes
    # Player 5 should have 1 vote
    # Player 2 should be banished
    
    assert handler.banished_id == 2
    assert game.players[1].is_alive is False # Player 2 (index 1) dead

def test_wolf_self_explode():
    gm = GameManager()
    game = gm.create_game()
    game.phase = GamePhase.SHERIFF_SPEECH
    game.sheriff_candidate_ids = [1, 2, 3]
    game.players[0].role = Role.WOLF # Player 1 is wolf
    
    handler = SheriffSpeechHandler(gm, game)
    handler.on_enter()
    
    # Player 1 explodes
    action = ActionRequest(player_id=1, type=ActionType.SELF_EXPLODE, timestamp=0)
    assert handler.process_action(action) is True
    
    assert game.players[0].is_alive is False
    assert game.election_explode_count == 1
    assert game.pending_sheriff_election is True
    
    # Should advance to Night
    assert handler.try_advance() == GamePhase.NIGHT_START

def test_double_wolf_self_explode():
    gm = GameManager()
    game = gm.create_game()
    game.phase = GamePhase.SHERIFF_SPEECH
    game.sheriff_candidate_ids = [1, 2, 3]
    game.players[0].role = Role.WOLF  # Player 1 is wolf
    game.players[1].role = Role.WOLF  # Player 2 is wolf (need 2 wolf candidates)
    game.election_explode_count = 1   # Already one explosion
    # Must track wolf candidates for double-explode rule
    game.election_wolf_candidates = [2, 1]  # Both wolves ran for sheriff

    handler = SheriffSpeechHandler(gm, game)
    handler.on_enter()

    # Player 1 explodes (Second explosion)
    action = ActionRequest(player_id=1, type=ActionType.SELF_EXPLODE, timestamp=0)
    assert handler.process_action(action) is True

    assert game.election_explode_count == 2
    assert game.election_cancelled is True  # Double explode cancels election
    assert game.pending_sheriff_election is False

    # Should advance to Night
    assert handler.try_advance() == GamePhase.NIGHT_START

if __name__ == "__main__":
    try:
        print("Running test_day_last_words_handler...")
        test_day_last_words_handler()
        print("Running test_sheriff_vote_weight...")
        test_sheriff_vote_weight()
        print("Running test_wolf_self_explode...")
        test_wolf_self_explode()
        print("Running test_double_wolf_self_explode...")
        test_double_wolf_self_explode()
        print("All new feature tests passed!")
    except AssertionError as e:
        print(f"Test failed: {e}")
    except Exception as e:
        print(f"Error: {e}")
