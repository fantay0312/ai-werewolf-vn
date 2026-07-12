from app.core.handlers.day_last_words import DayLastWordsHandler
from app.core.handlers.day_pk_speech import DayPKSpeechHandler
from app.models.action_model import ActionRequest
from app.models.game_state import ActionType, GamePhase, GameState, Player, Role


def _player(
    player_id: int,
    role: Role,
    *,
    alive: bool = True,
) -> Player:
    return Player(
        id=player_id,
        name=f"{player_id}号玩家",
        role=role,
        portrait="",
        is_alive=alive,
    )


def _find_event_log(game: GameState, event_name: str):
    for log in reversed(game.game_logs):
        if log.data and log.data.get("event") == event_name:
            return log
    raise AssertionError(f"event log not found: {event_name}")


def test_day_last_words_emits_structured_window_and_turn_metadata():
    game = GameState(
        session_id="last-words",
        day=2,
        phase=GamePhase.DAY_LAST_WORDS,
        players=[
            _player(1, Role.VILLAGER, alive=False),
            _player(2, Role.SEER, alive=False),
            _player(3, Role.WITCH),
        ],
        dead_players=[2, 1],
    )

    handler = DayLastWordsHandler(None, game)
    handler.on_enter()

    start_log = _find_event_log(game, "day_last_words_started")
    assert start_log.data["eligible_speaker_ids"] == [1, 2]
    assert start_log.data["speaking_order"] == [1, 2]
    assert start_log.data["current_speaker_id"] == 1
    assert start_log.data["next_phase_hint"] == GamePhase.DAY_DISCUSS.value
    assert game.players[0].has_acted is False
    assert game.players[1].has_acted is True

    assert handler.process_action(ActionRequest(player_id=1, type=ActionType.SPEECH, content="遗言")) is True
    speech_log = _find_event_log(game, "day_last_words_speech")
    assert speech_log.data["speaker_id"] == 1
    assert speech_log.data["speaker_index"] == 0
    assert speech_log.data["next_speaker_id"] == 2
    assert speech_log.data["next_phase_hint"] == GamePhase.DAY_DISCUSS.value
    assert game.current_speaker_index == 1
    assert game.players[1].has_acted is False

    assert handler.process_action(ActionRequest(player_id=2, type=ActionType.PASS)) is True
    end_log = _find_event_log(game, "day_last_words_turn_end")
    assert end_log.data["action"] == ActionType.PASS.value
    assert end_log.data["speaker_id"] == 2
    assert end_log.data["next_speaker_id"] is None
    assert end_log.data["next_phase_hint"] == GamePhase.DAY_DISCUSS.value
    assert handler.try_advance() == GamePhase.DAY_DISCUSS


def test_day_pk_speech_emits_structured_window_and_turn_metadata():
    game = GameState(
        session_id="pk-speech",
        day=3,
        phase=GamePhase.DAY_PK_SPEECH,
        players=[
            _player(1, Role.VILLAGER),
            _player(2, Role.WOLF),
            _player(3, Role.SEER),
        ],
        pk_candidates=[2, 1],
        pk_round=1,
    )

    handler = DayPKSpeechHandler(None, game)
    handler.on_enter()

    start_log = _find_event_log(game, "day_pk_speech_started")
    assert start_log.data["pk_candidate_ids"] == [1, 2]
    assert start_log.data["pk_round"] == 1
    assert start_log.data["speaking_order"] == [1, 2]
    assert start_log.data["current_speaker_id"] == 1
    assert start_log.data["next_phase_hint"] == GamePhase.DAY_PK_VOTE.value
    assert game.players[0].has_acted is False
    assert game.players[1].has_acted is True

    assert handler.process_action(ActionRequest(player_id=1, type=ActionType.SPEECH, content="PK发言")) is True
    speech_log = _find_event_log(game, "day_pk_speech")
    assert speech_log.data["speaker_id"] == 1
    assert speech_log.data["speaker_index"] == 0
    assert speech_log.data["pk_candidate_ids"] == [2, 1]
    assert speech_log.data["next_speaker_id"] == 2
    assert speech_log.data["next_phase_hint"] == GamePhase.DAY_PK_VOTE.value
    assert game.players[1].has_acted is False

    assert handler.process_action(ActionRequest(player_id=2, type=ActionType.CONFIRM)) is True
    end_log = _find_event_log(game, "day_pk_speech_turn_end")
    assert end_log.data["action"] == ActionType.CONFIRM.value
    assert end_log.data["speaker_id"] == 2
    assert end_log.data["next_speaker_id"] is None
    assert end_log.data["next_phase_hint"] == GamePhase.DAY_PK_VOTE.value
    assert handler.try_advance() == GamePhase.DAY_PK_VOTE
