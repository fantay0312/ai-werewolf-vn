from app.core.game_manager import GameManager
from app.core.handlers.day_pk_vote import DayPKVoteHandler
from app.core.handlers.day_pk_result import DayPKResultHandler
from app.models.action_model import ActionRequest
from app.models.game_state import ActionType, GamePhase


def test_day_pk_vote_logs_include_start_and_cast_metadata():
    gm = GameManager()
    game = gm.create_game()
    game.phase = GamePhase.DAY_PK_VOTE
    game.game_logs = []
    game.pk_candidates = [1, 2]
    game.pk_round = 1

    handler = DayPKVoteHandler(gm, game)
    handler.on_enter()

    eligible_voter_ids = [player.id for player in game.players if player.is_alive and player.id not in game.pk_candidates]
    voter_id = eligible_voter_ids[0]
    target_id = game.pk_candidates[0]

    assert handler.process_action(
        ActionRequest(player_id=voter_id, type=ActionType.VOTE, target_id=target_id)
    )

    start_log = game.game_logs[0]
    cast_log = game.game_logs[-1]

    assert start_log.data["event"] == "day_pk_vote_started"
    assert start_log.data["participant_ids"] == eligible_voter_ids
    assert start_log.data["eligible_voter_ids"] == eligible_voter_ids
    assert start_log.data["eligible_target_ids"] == [1, 2]
    assert start_log.data["pk_candidate_ids"] == [1, 2]
    assert start_log.data["pk_round"] == 1

    assert cast_log.data["event"] == "day_pk_vote_cast"
    assert cast_log.data["action"] == ActionType.VOTE.value
    assert cast_log.data["voter_id"] == voter_id
    assert cast_log.data["target_id"] == target_id
    assert cast_log.data["target_label"] == f"{target_id}号"
    assert cast_log.data["pk_candidate_ids"] == [1, 2]
    assert cast_log.data["pk_round"] == 1
    assert cast_log.data["votes"] == {voter_id: target_id}
    assert cast_log.data["pk_votes"] == {voter_id: target_id}
    assert cast_log.data["vote_counts"] == {target_id: 1}
    assert cast_log.data["is_abstain"] is False


def test_day_pk_result_logs_include_tally_and_exile_metadata():
    gm = GameManager()
    game = gm.create_game()
    game.phase = GamePhase.DAY_PK_RESULT
    game.game_logs = []
    game.pk_candidates = [2, 5]
    game.pk_round = 1
    game.sheriff_id = 1
    game.players[0].is_sheriff = True
    game.pk_votes = {1: 2, 3: 2, 4: 5}

    handler = DayPKResultHandler(gm, game)
    handler.on_enter()

    tally_log = game.game_logs[0]
    exile_log = game.game_logs[-1]

    assert tally_log.data["event"] == "day_pk_vote_tallied"
    assert tally_log.is_public is True
    assert tally_log.data["votes"] == {1: 2, 3: 2, 4: 5}
    assert tally_log.data["pk_votes"] == {1: 2, 3: 2, 4: 5}
    assert tally_log.data["vote_counts"] == {2: 3, 5: 1}
    assert tally_log.data["pk_candidate_ids"] == [2, 5]
    assert tally_log.data["pk_round"] == 1
    assert tally_log.data["outcome"] == "exile"

    assert exile_log.data["event"] == "day_pk_vote_exiled"
    assert exile_log.data["banished_id"] == 2
    assert exile_log.data["winner_id"] == 2
    assert exile_log.data["target_id"] == 2
    assert exile_log.data["candidate_ids"] == [2]
    assert exile_log.data["pk_candidate_ids"] == [2, 5]
    assert exile_log.data["dead_players"] == [2]
    assert exile_log.data["dead_player_ids"] == [2]
    assert exile_log.data["outcome"] == "exiled"


def test_day_pk_result_logs_include_tie_metadata():
    gm = GameManager()
    game = gm.create_game()
    game.phase = GamePhase.DAY_PK_RESULT
    game.game_logs = []
    game.pk_candidates = [2, 5]
    game.pk_round = 1
    game.pk_votes = {1: 2, 3: 2, 4: 5, 6: 5}

    handler = DayPKResultHandler(gm, game)
    handler.on_enter()

    tie_log = game.game_logs[-1]

    assert tie_log.data["event"] == "day_pk_vote_tied"
    assert tie_log.data["candidate_ids"] == [2, 5]
    assert tie_log.data["tied_candidate_ids"] == [2, 5]
    assert tie_log.data["pk_candidate_ids"] == [2, 5]
    assert tie_log.data["pk_candidate_count"] == 2
    assert tie_log.data["pk_round"] == 1
    assert tie_log.data["outcome"] == "tie_no_elimination"
    assert tie_log.data["next_phase"] == GamePhase.NIGHT_START.value


def test_day_pk_result_logs_include_no_elimination_metadata_for_abstains():
    gm = GameManager()
    game = gm.create_game()
    game.phase = GamePhase.DAY_PK_RESULT
    game.game_logs = []
    game.pk_candidates = [2, 5]
    game.pk_round = 1
    game.pk_votes = {1: 0, 3: 0, 4: 0}

    handler = DayPKResultHandler(gm, game)
    handler.on_enter()

    result_log = game.game_logs[-1]

    assert result_log.data["event"] == "day_pk_vote_no_elimination"
    assert result_log.data["reason"] == "all_abstained"
    assert result_log.data["pk_candidate_ids"] == [2, 5]
    assert result_log.data["pk_round"] == 1
    assert result_log.data["votes"] == {1: 0, 3: 0, 4: 0}
    assert result_log.data["pk_votes"] == {1: 0, 3: 0, 4: 0}
    assert result_log.data["abstain_voter_ids"] == [1, 3, 4]
    assert result_log.data["abstain_count"] == 3
    assert result_log.data["counted_ballots"] == 0
    assert result_log.data["outcome"] == "no_elimination"
    assert result_log.data["next_phase"] == GamePhase.NIGHT_START.value


def test_day_pk_result_logs_include_error_metadata_when_winner_missing():
    gm = GameManager()
    game = gm.create_game()
    game.phase = GamePhase.DAY_PK_RESULT
    game.game_logs = []
    game.players = game.players[:3]
    game.pk_candidates = [99, 100]
    game.pk_round = 1
    game.pk_votes = {1: 99, 2: 99}

    handler = DayPKResultHandler(gm, game)
    handler.on_enter()

    error_log = game.game_logs[-1]

    assert error_log.data["event"] == "day_pk_vote_result_error"
    assert error_log.data["winner_id"] == 99
    assert error_log.data["target_id"] == 99
    assert error_log.data["max_votes"] == 2
    assert error_log.data["candidate_ids"] == [99]
    assert error_log.data["pk_candidate_ids"] == [99, 100]
    assert error_log.data["pk_round"] == 1
    assert error_log.data["outcome"] == "error"
    assert error_log.data["next_phase"] == GamePhase.NIGHT_START.value
