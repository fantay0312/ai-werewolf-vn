from app.core.handlers.night_seer import NightSeerHandler
from app.core.handlers.sheriff_vote import SheriffVoteHandler
from app.models.action_model import ActionRequest
from app.models.game_state import ActionType, GamePhase, GameState, Player, Role


def _latest_event(game: GameState, event: str):
    for log in reversed(game.game_logs):
        if log.data and log.data.get("event") == event:
            return log
    raise AssertionError(f"missing event log: {event}")


def test_sheriff_vote_structured_events_for_election_and_abstain():
    game = GameState(
        session_id="sheriff-vote",
        day=1,
        phase=GamePhase.SHERIFF_VOTE,
        players=[
            Player(id=1, name="C1", role=Role.VILLAGER, portrait=""),
            Player(id=2, name="C2", role=Role.VILLAGER, portrait=""),
            Player(id=3, name="V3", role=Role.VILLAGER, portrait=""),
            Player(id=4, name="V4", role=Role.VILLAGER, portrait=""),
        ],
        sheriff_candidate_ids=[1, 2],
    )
    handler = SheriffVoteHandler(None, game)
    handler.on_enter()

    start_log = _latest_event(game, "sheriff_vote_started")
    assert start_log.data["candidate_ids"] == [1, 2]
    assert start_log.data["eligible_voter_ids"] == [3, 4]
    assert start_log.data["eligible_target_ids"] == [1, 2]
    assert start_log.data["allow_abstain"] is True
    assert start_log.data["next_phase_hint"] == GamePhase.NIGHT_START.value

    assert handler.process_action(ActionRequest(player_id=3, type=ActionType.VOTE, target_id=1)) is True
    cast_log = _latest_event(game, "sheriff_vote_cast")
    assert cast_log.data["voter_id"] == 3
    assert cast_log.data["target_id"] == 1
    assert cast_log.data["target_label"] == "1号"
    assert cast_log.data["is_abstain"] is False

    assert handler.process_action(ActionRequest(player_id=4, type=ActionType.VOTE)) is True
    abstain_log = _latest_event(game, "sheriff_vote_cast")
    assert abstain_log.data["voter_id"] == 4
    assert abstain_log.data["target_id"] == 0
    assert abstain_log.data["target_label"] == "弃票"
    assert abstain_log.data["is_abstain"] is True

    assert handler.try_advance() == GamePhase.NIGHT_START
    tally_log = _latest_event(game, "sheriff_vote_tallied")
    assert tally_log.data["votes"] == {3: 1, 4: 0}
    assert tally_log.data["vote_entries"] == [
        {"voter_id": 3, "target_id": 1, "target_label": "1号", "weight": 1},
        {"voter_id": 4, "target_id": 0, "target_label": "弃票", "weight": 1},
    ]
    assert tally_log.is_public is True
    assert tally_log.data["abstain_voter_ids"] == [4]
    assert tally_log.data["abstain_count"] == 1
    elected_log = _latest_event(game, "sheriff_elected")
    assert elected_log.data["sheriff_id"] == 1
    assert elected_log.data["candidate_ids"] == [1]
    assert elected_log.data["vote_count"] == 1
    assert game.sheriff_id == 1


def test_sheriff_vote_structured_tie_and_empty():
    tie_game = GameState(
        session_id="sheriff-vote-tie",
        day=1,
        phase=GamePhase.SHERIFF_VOTE,
        players=[
            Player(id=1, name="C1", role=Role.VILLAGER, portrait=""),
            Player(id=2, name="C2", role=Role.VILLAGER, portrait=""),
            Player(id=3, name="V3", role=Role.VILLAGER, portrait=""),
            Player(id=4, name="V4", role=Role.VILLAGER, portrait=""),
        ],
        sheriff_candidate_ids=[1, 2],
    )
    tie_handler = SheriffVoteHandler(None, tie_game)
    tie_handler.on_enter()
    assert tie_handler.process_action(ActionRequest(player_id=3, type=ActionType.VOTE, target_id=1)) is True
    assert tie_handler.process_action(ActionRequest(player_id=4, type=ActionType.VOTE, target_id=2)) is True
    assert tie_handler.try_advance() == GamePhase.NIGHT_START
    tie_log = _latest_event(tie_game, "sheriff_vote_tied")
    assert sorted(tie_log.data["candidate_ids"]) == [1, 2]
    assert tie_log.data["vote_count"] == 1

    empty_game = GameState(
        session_id="sheriff-vote-empty",
        day=1,
        phase=GamePhase.SHERIFF_VOTE,
        players=[
            Player(id=1, name="C1", role=Role.VILLAGER, portrait=""),
            Player(id=2, name="C2", role=Role.VILLAGER, portrait=""),
            Player(id=3, name="V3", role=Role.VILLAGER, portrait=""),
        ],
        sheriff_candidate_ids=[1, 2],
    )
    empty_handler = SheriffVoteHandler(None, empty_game)
    empty_handler.on_enter()
    assert empty_handler.process_action(ActionRequest(player_id=3, type=ActionType.VOTE)) is True
    assert empty_handler.try_advance() == GamePhase.NIGHT_START
    empty_log = _latest_event(empty_game, "sheriff_vote_empty")
    assert empty_log.data["votes"] == {3: 0}
    assert empty_log.data["vote_counts"] == {}


def test_night_seer_structured_prompt_check_and_pass():
    seer = Player(id=1, name="Seer", role=Role.SEER, portrait="")
    villager = Player(id=2, name="Villager", role=Role.VILLAGER, portrait="")
    wolf = Player(id=3, name="Wolf", role=Role.WOLF, portrait="")

    game = GameState(
        session_id="seer-check",
        day=1,
        phase=GamePhase.NIGHT_SEER,
        players=[seer, villager, wolf],
    )
    handler = NightSeerHandler(None, game)
    handler.on_enter()

    prompt_log = _latest_event(game, "seer_prompted")
    assert prompt_log.data["seer_id"] == 1
    assert prompt_log.data["allowed_target_ids"] == [1, 2, 3]
    assert prompt_log.data["next_phase_hint"] == GamePhase.NIGHT_WITCH.value

    assert handler.process_action(ActionRequest(player_id=1, type=ActionType.CHECK, target_id=3)) is True
    check_log = _latest_event(game, "seer_checked")
    assert check_log.data["action"] == "seer_check"
    assert check_log.data["target_id"] == 3
    assert check_log.data["result"] == "bad"
    assert check_log.data["result_text"] == "狼人"

    pass_game = GameState(
        session_id="seer-pass",
        day=2,
        phase=GamePhase.NIGHT_SEER,
        players=[Player(id=4, name="SeerPass", role=Role.SEER, portrait=""), villager],
    )
    pass_handler = NightSeerHandler(None, pass_game)
    pass_handler.on_enter()
    assert pass_handler.process_action(ActionRequest(player_id=4, type=ActionType.PASS)) is True
    pass_log = _latest_event(pass_game, "seer_passed")
    assert pass_log.data["action"] == "pass"
    assert pass_log.data["actor_id"] == 4
    assert pass_log.data["next_phase_hint"] == GamePhase.NIGHT_WITCH.value
