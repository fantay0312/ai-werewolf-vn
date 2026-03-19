from unittest.mock import patch

from app.core.handlers.day_discuss import DayDiscussHandler
from app.core.handlers.night_wolf_discuss import NightWolfDiscussHandler
from app.core.handlers.night_wolf_vote import NightWolfVoteHandler
from app.core.handlers.sheriff_speech import SheriffSpeechHandler
from app.models.action_model import ActionRequest
from app.models.game_state import ActionType, GamePhase, GameState, Player, Role


class _DummyJudgeSystem:
    def __init__(self, order):
        self._order = order

    def determine_speaking_order(self, alive_ids, sheriff_id=None):
        return list(self._order)


class _DummyGameManager:
    def __init__(self, order):
        self.judge_system = _DummyJudgeSystem(order)


def test_day_discuss_enforces_turn_order_and_logs_structured_events():
    game = GameState(
        session_id="test",
        day=2,
        phase=GamePhase.DAY_DISCUSS,
        players=[
            Player(id=1, name="P1", role=Role.VILLAGER, portrait=""),
            Player(id=2, name="P2", role=Role.VILLAGER, portrait=""),
        ],
    )
    handler = DayDiscussHandler(_DummyGameManager([2, 1]), game)
    handler.on_enter()

    assert game.speaking_order == [2, 1]
    assert game.players[0].has_acted is True
    assert game.players[1].has_acted is False

    out_of_turn = ActionRequest(player_id=1, type=ActionType.SPEECH, content="抢话")
    assert handler.process_action(out_of_turn) is False

    action = ActionRequest(player_id=2, type=ActionType.SPEECH, content="我先说")
    assert handler.process_action(action) is True

    log = game.game_logs[-1]
    assert log.data is not None
    assert log.data["event"] == "day_discuss_speech"
    assert log.data["action"] == "speech"
    assert log.data["speaker_id"] == 2
    assert log.data["speaker_index"] == 0
    assert log.data["next_speaker_id"] == 1
    assert game.current_speaker_index == 1
    assert game.players[0].has_acted is False

    end_turn = ActionRequest(player_id=1, type=ActionType.PASS)
    assert handler.process_action(end_turn) is True
    assert handler.try_advance() == GamePhase.DAY_VOTE


def test_sheriff_speech_enforces_turn_order_and_tracks_withdrawal():
    game = GameState(
        session_id="test",
        day=1,
        phase=GamePhase.SHERIFF_SPEECH,
        players=[
            Player(id=1, name="P1", role=Role.VILLAGER, portrait=""),
            Player(id=2, name="P2", role=Role.VILLAGER, portrait=""),
            Player(id=3, name="P3", role=Role.VILLAGER, portrait=""),
        ],
        sheriff_candidate_ids=[1, 2],
    )
    handler = SheriffSpeechHandler(None, game)
    handler.on_enter()

    assert game.speaking_order == [1, 2]
    assert handler.process_action(ActionRequest(player_id=2, type=ActionType.SPEECH, content="越位")) is False

    withdraw = ActionRequest(player_id=1, type=ActionType.WITHDRAW)
    assert handler.process_action(withdraw) is True
    log = game.game_logs[-1]
    assert log.data is not None
    assert log.data["event"] == "sheriff_withdraw"
    assert log.data["remaining_candidate_ids"] == [2]
    assert log.data["next_speaker_id"] == 2
    assert game.players[1].has_acted is False

    speech = ActionRequest(player_id=2, type=ActionType.SPEECH, content="继续竞选")
    assert handler.process_action(speech) is True
    assert handler.try_advance() == GamePhase.SHERIFF_VOTE


def test_wolf_discuss_and_vote_emit_structured_events():
    discuss_game = GameState(
        session_id="wolf-discuss",
        day=1,
        phase=GamePhase.NIGHT_WOLF_DISCUSS,
        players=[
            Player(id=1, name="W1", role=Role.WOLF, portrait=""),
            Player(id=2, name="W2", role=Role.WOLF_KING, portrait=""),
            Player(id=3, name="V3", role=Role.VILLAGER, portrait=""),
            Player(id=4, name="V4", role=Role.VILLAGER, portrait=""),
        ],
    )
    discuss_handler = NightWolfDiscussHandler(None, discuss_game)
    discuss_handler.on_enter()
    assert discuss_game.game_logs[-1].data["event"] == "wolf_discuss_round_started"

    speech = ActionRequest(player_id=1, type=ActionType.SPEECH, content="今晚刀3号")
    assert discuss_handler.process_action(speech) is True
    speech_log = discuss_game.game_logs[-1]
    assert speech_log.data is not None
    assert speech_log.data["event"] == "wolf_discuss_speech"
    assert speech_log.data["mentioned_player_ids"] == [3]

    vote_game = GameState(
        session_id="wolf-vote",
        day=1,
        phase=GamePhase.NIGHT_WOLF_VOTE,
        players=[
            Player(id=1, name="W1", role=Role.WOLF, portrait=""),
            Player(id=2, name="W2", role=Role.WOLF_KING, portrait=""),
            Player(id=3, name="V3", role=Role.VILLAGER, portrait=""),
            Player(id=4, name="V4", role=Role.VILLAGER, portrait=""),
        ],
    )
    vote_handler = NightWolfVoteHandler(None, vote_game)
    vote_handler.on_enter()
    assert vote_game.game_logs[-1].data["event"] == "wolf_vote_started"

    assert vote_handler.process_action(ActionRequest(player_id=1, type=ActionType.KILL, target_id=3)) is True
    cast_log = vote_game.game_logs[-1]
    assert cast_log.data is not None
    assert cast_log.data["event"] == "wolf_vote_cast"
    assert cast_log.data["votes"] == {1: 3}

    assert vote_handler.process_action(ActionRequest(player_id=2, type=ActionType.KILL, target_id=4)) is True
    with patch("app.core.handlers.night_wolf_vote.random.choice", return_value=vote_game.players[0]):
        assert vote_handler.try_advance() is None
    tie_log = vote_game.game_logs[-1]
    assert tie_log.data is not None
    assert tie_log.data["event"] == "wolf_vote_tied"
    assert tie_log.data["resolver_id"] == 1

    assert vote_handler.process_action(ActionRequest(player_id=1, type=ActionType.KILL, target_id=4)) is True
    assert vote_handler.try_advance() == GamePhase.NIGHT_SEER
    result_log = vote_game.game_logs[-1]
    assert result_log.data is not None
    assert result_log.data["event"] == "wolf_vote_resolved"
    assert result_log.data["target_id"] == 4
