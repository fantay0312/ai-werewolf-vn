from app.core.handlers.day_start import DayStartHandler
from app.core.handlers.game_start import GameStartHandler
from app.core.handlers.night_start import NightStartHandler
from app.core.handlers.sheriff_election import SheriffElectionHandler
from app.models.action_model import ActionRequest
from app.models.game_state import ActionType, GamePhase, GameState, Player, Role


def _player(player_id: int, role: Role, *, human: bool = False, alive: bool = True) -> Player:
    return Player(
        id=player_id,
        name=f"{player_id}号玩家",
        role=role,
        portrait="",
        is_human=human,
        is_alive=alive,
    )


def _find_event_log(logs, event_name: str):
    for log in reversed(logs):
        if log.data and log.data.get("event") == event_name:
            return log
    raise AssertionError(f"Missing structured log {event_name!r}: {[log.data for log in logs]}")


def test_game_start_emits_structured_prompt_and_acknowledgement():
    game = GameState(
        session_id="game-start",
        day=1,
        phase=GamePhase.GAME_START,
        players=[
            _player(1, Role.VILLAGER, human=True),
            _player(2, Role.WOLF),
            _player(3, Role.SEER),
        ],
    )
    handler = GameStartHandler(None, game)

    handler.on_enter()
    prompt_log = _find_event_log(game.game_logs, "game_start_prompt")
    assert prompt_log.data["participant_ids"] == [1, 2, 3]
    assert prompt_log.data["human_player_id"] == 1
    assert prompt_log.data["required_action"] == ActionType.CONFIRM.value
    assert prompt_log.data["next_phase_hint"] == GamePhase.SHERIFF_ELECTION.value

    assert handler.process_action(ActionRequest(player_id=1, type=ActionType.CONFIRM)) is True
    ack_log = _find_event_log(game.game_logs, "game_start_acknowledged")
    assert ack_log.data["action"] == ActionType.CONFIRM.value
    assert ack_log.data["player_id"] == 1
    assert ack_log.data["human_confirmed"] is True
    assert ack_log.data["advance_condition_met"] is True
    assert ack_log.data["next_phase_hint"] == GamePhase.SHERIFF_ELECTION.value
    assert handler.try_advance() == GamePhase.SHERIFF_ELECTION


def test_night_start_emits_structured_reset_summary():
    players = [
        _player(1, Role.VILLAGER),
        _player(2, Role.WOLF),
        _player(3, Role.SEER, alive=False),
    ]
    players[0].has_acted = True
    players[0].protected_by_guard = True
    players[1].killed_by_wolf = True
    players[1].poisoned_by_witch = True
    players[1].saved_by_witch = True
    players[1].checked_by_seer = True

    game = GameState(
        session_id="night-start",
        day=2,
        phase=GamePhase.NIGHT_START,
        players=players,
        sheriff_id=1,
        wolf_kill_target=2,
        votes={1: 2},
    )
    game.wolf_discuss_messages = [object()]  # only count matters

    handler = NightStartHandler(None, game)
    handler.on_enter()

    log = _find_event_log(game.game_logs, "night_started")
    assert log.data["night_number"] == 2
    assert log.data["alive_player_ids"] == [1, 2]
    assert log.data["dead_player_ids"] == [3]
    assert log.data["sheriff_id"] == 1
    assert log.data["wolf_kill_target"] is None
    assert log.data["votes"] == {}
    assert log.data["wolf_discuss_message_count"] == 0
    assert log.data["next_phase_hint"] == GamePhase.NIGHT_WOLF_DISCUSS.value
    assert game.wolf_kill_target is None
    assert game.votes == {}
    assert game.wolf_discuss_messages == []
    assert players[0].protected_by_guard is False
    assert players[1].checked_by_seer is False


def test_day_start_emits_structured_summary_and_acknowledgement():
    game = GameState(
        session_id="day-start",
        day=1,
        phase=GamePhase.DAY_START,
        players=[
            _player(1, Role.VILLAGER, human=True),
            _player(2, Role.WOLF),
            _player(3, Role.SEER),
        ],
        dead_players=[],
    )
    handler = DayStartHandler(None, game)

    handler.on_enter()
    start_log = _find_event_log(game.game_logs, "day_started")
    assert start_log.data["is_peaceful_night"] is True
    assert start_log.data["dead_player_ids"] == []
    assert start_log.data["winner"] is None
    assert start_log.data["next_phase_hint"] == GamePhase.DAY_DISCUSS.value

    assert handler.process_action(ActionRequest(player_id=1, type=ActionType.CONFIRM)) is True
    ack_log = _find_event_log(game.game_logs, "day_start_acknowledged")
    assert ack_log.data["action"] == ActionType.CONFIRM.value
    assert ack_log.data["player_id"] == 1
    assert ack_log.data["advance_condition"] == "any_confirm"
    assert ack_log.data["next_phase_hint"] == GamePhase.DAY_DISCUSS.value


def test_sheriff_election_emits_structured_start_actions_and_close():
    game = GameState(
        session_id="sheriff-election",
        day=1,
        phase=GamePhase.SHERIFF_ELECTION,
        players=[
            _player(1, Role.VILLAGER),
            _player(2, Role.WOLF),
            _player(3, Role.SEER),
        ],
    )
    handler = SheriffElectionHandler(None, game)

    handler.on_enter()
    start_log = _find_event_log(game.game_logs, "sheriff_election_started")
    assert start_log.data["participant_ids"] == [1, 2, 3]
    assert start_log.data["next_phase_if_has_candidates"] == GamePhase.SHERIFF_SPEECH.value
    assert start_log.data["next_phase_if_no_candidates"] == GamePhase.NIGHT_START.value

    assert handler.process_action(ActionRequest(player_id=2, type=ActionType.RUN_FOR_SHERIFF)) is True
    candidate_log = _find_event_log(game.game_logs, "sheriff_candidacy_declared")
    assert candidate_log.data["action"] == ActionType.RUN_FOR_SHERIFF.value
    assert candidate_log.data["player_id"] == 2
    assert candidate_log.data["is_wolf_candidate"] is True
    assert candidate_log.data["sheriff_candidate_ids"] == [2]
    assert candidate_log.data["wolf_candidate_ids"] == [2]

    assert handler.process_action(ActionRequest(player_id=1, type=ActionType.PASS)) is True
    assert handler.process_action(ActionRequest(player_id=3, type=ActionType.PASS)) is True
    pass_log = _find_event_log(game.game_logs, "sheriff_election_passed")
    assert pass_log.data["all_acted"] is True
    assert pass_log.data["next_phase_hint"] == GamePhase.SHERIFF_SPEECH.value

    assert handler.try_advance() == GamePhase.SHERIFF_SPEECH
    closed_log = _find_event_log(game.game_logs, "sheriff_election_closed")
    assert closed_log.data["outcome"] == "speech_required"
    assert closed_log.data["sheriff_candidate_ids"] == [2]
    assert closed_log.data["next_phase_hint"] == GamePhase.SHERIFF_SPEECH.value


def test_sheriff_election_cancelled_emits_structured_summary():
    game = GameState(
        session_id="sheriff-cancelled",
        day=1,
        phase=GamePhase.SHERIFF_ELECTION,
        players=[
            _player(1, Role.VILLAGER),
            _player(2, Role.WOLF),
        ],
        election_cancelled=True,
        election_explode_count=2,
        election_wolf_candidates=[2],
    )
    handler = SheriffElectionHandler(None, game)

    handler.on_enter()
    log = _find_event_log(game.game_logs, "sheriff_election_cancelled")
    assert log.data["reason"] == "double_self_explode"
    assert log.data["election_explode_count"] == 2
    assert log.data["wolf_candidate_ids"] == [2]
    assert log.data["next_phase_hint"] == GamePhase.NIGHT_START.value
    assert handler.try_advance() == GamePhase.NIGHT_START
