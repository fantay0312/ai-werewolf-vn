from app.core.game_manager import GameManager
from app.core.handlers.day_vote import DayVoteHandler
from app.core.handlers.day_vote_result import DayVoteResultHandler
from app.models.action_model import ActionRequest
from app.models.game_state import ActionType, GamePhase


def test_day_vote_logs_include_start_and_cast_metadata():
    gm = GameManager()
    game = gm.create_game()
    game.phase = GamePhase.DAY_VOTE
    game.game_logs = []

    handler = DayVoteHandler(gm, game)
    handler.on_enter()

    alive_ids = [player.id for player in game.players if player.is_alive]
    voter_id = alive_ids[0]
    target_id = alive_ids[1]

    assert handler.process_action(
        ActionRequest(player_id=voter_id, type=ActionType.VOTE, target_id=target_id)
    )

    start_log = game.game_logs[0]
    cast_log = game.game_logs[-1]

    assert start_log.data["event"] == "day_vote_started"
    assert start_log.data["participant_ids"] == alive_ids
    assert start_log.data["eligible_voter_ids"] == alive_ids
    assert start_log.data["eligible_voter_count"] == len(alive_ids)
    assert start_log.data["eligible_target_ids"] == alive_ids
    assert start_log.data["allow_abstain"] is True

    assert cast_log.type == "action"
    assert cast_log.player_id == voter_id
    assert cast_log.data["event"] == "day_vote_cast"
    assert cast_log.data["action"] == ActionType.VOTE.value
    assert cast_log.data["voter_id"] == voter_id
    assert cast_log.data["target_id"] == target_id
    assert cast_log.data["target_label"] == f"{target_id}号"
    assert cast_log.data["votes"] == {voter_id: target_id}
    assert cast_log.data["votes_snapshot"] == {voter_id: target_id}
    assert cast_log.data["vote_counts"] == {target_id: 1}
    assert cast_log.data["is_abstain"] is False
    assert cast_log.data["vote_progress"]["acted_count"] == 1
    assert voter_id in cast_log.data["vote_progress"]["acted_player_ids"]


def test_day_vote_result_logs_include_tally_and_exile_metadata():
    gm = GameManager()
    game = gm.create_game()
    game.phase = GamePhase.DAY_VOTE_RESULT
    game.game_logs = []
    game.sheriff_id = 1
    game.players[0].is_sheriff = True
    game.votes = {1: 2, 3: 2, 4: 5}

    handler = DayVoteResultHandler(gm, game)
    handler.on_enter()

    tally_log = game.game_logs[0]
    exile_log = game.game_logs[-1]

    assert tally_log.data["event"] == "day_vote_tallied"
    assert tally_log.data["votes"] == {1: 2, 3: 2, 4: 5}
    assert tally_log.data["vote_counts"] == {2: 3, 5: 1}
    assert tally_log.data["abstain_count"] == 0
    assert tally_log.data["max_votes"] == 3
    assert tally_log.data["leading_candidate_ids"] == [2]
    assert tally_log.data["outcome"] == "exile"
    assert tally_log.data["vote_entries"][0] == {
        "voter_id": 1,
        "target_id": 2,
        "target_label": "2号",
        "weight": 2,
        "is_sheriff_vote": True,
    }

    assert exile_log.data["event"] == "day_vote_exiled"
    assert exile_log.data["banished_id"] == 2
    assert exile_log.data["winner_id"] == 2
    assert exile_log.data["target_id"] == 2
    assert exile_log.data["max_votes"] == 3
    assert exile_log.data["candidate_ids"] == [2]
    assert exile_log.data["vote_counts"] == {2: 3, 5: 1}
    assert exile_log.data["dead_players"] == [2]
    assert exile_log.data["dead_player_ids"] == [2]
    assert exile_log.data["outcome"] == "exiled"


def test_day_vote_result_logs_include_tie_metadata():
    gm = GameManager()
    game = gm.create_game()
    game.phase = GamePhase.DAY_VOTE_RESULT
    game.game_logs = []
    game.votes = {1: 2, 3: 2, 4: 5, 6: 5}

    handler = DayVoteResultHandler(gm, game)
    handler.on_enter()

    tie_log = game.game_logs[-1]

    assert tie_log.data["event"] == "day_vote_tied"
    assert tie_log.data["max_votes"] == 2
    assert tie_log.data["candidate_ids"] == [2, 5]
    assert tie_log.data["tied_candidate_ids"] == [2, 5]
    assert tie_log.data["pk_candidate_ids"] == [2, 5]
    assert tie_log.data["pk_candidate_count"] == 2
    assert tie_log.data["pk_round"] == 1
    assert tie_log.data["outcome"] == "pk_required"
    assert tie_log.data["next_phase"] == GamePhase.DAY_PK_SPEECH.value


def test_day_vote_result_logs_include_no_elimination_metadata_for_abstains():
    gm = GameManager()
    game = gm.create_game()
    game.phase = GamePhase.DAY_VOTE_RESULT
    game.game_logs = []
    game.votes = {1: 0, 2: 0, 3: 0}

    handler = DayVoteResultHandler(gm, game)
    handler.on_enter()

    result_log = game.game_logs[-1]

    assert result_log.data["event"] == "day_vote_no_elimination"
    assert result_log.data["reason"] == "all_abstained"
    assert result_log.data["votes"] == {1: 0, 2: 0, 3: 0}
    assert result_log.data["abstain_voter_ids"] == [1, 2, 3]
    assert result_log.data["abstain_count"] == 3
    assert result_log.data["counted_ballots"] == 0
    assert result_log.data["outcome"] == "no_elimination"
    assert result_log.data["next_phase"] == GamePhase.NIGHT_START.value


def test_day_vote_result_logs_include_error_metadata_when_winner_missing():
    gm = GameManager()
    game = gm.create_game()
    game.phase = GamePhase.DAY_VOTE_RESULT
    game.game_logs = []
    game.players = game.players[:3]
    game.votes = {1: 99, 2: 99}

    handler = DayVoteResultHandler(gm, game)
    handler.on_enter()

    error_log = game.game_logs[-1]

    assert error_log.data["event"] == "day_vote_result_error"
    assert error_log.data["winner_id"] == 99
    assert error_log.data["target_id"] == 99
    assert error_log.data["max_votes"] == 2
    assert error_log.data["candidate_ids"] == [99]
    assert error_log.data["outcome"] == "error"
    assert error_log.data["next_phase"] == GamePhase.NIGHT_START.value
