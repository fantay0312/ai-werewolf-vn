"""Regression tests for exile last words, dead-sheriff badge convergence,
and the wolf_discuss_round field lifecycle."""

from app.core.game_manager import GameManager
from app.core.handlers.day_last_words import DayLastWordsHandler
from app.core.handlers.day_vote_result import DayVoteResultHandler
from app.core.handlers.night_wolf_discuss import NightWolfDiscussHandler
from app.core.handlers.sheriff_transfer import SheriffTransferHandler
from app.models.game_state import ActionType, GamePhase, GameState, Player, Role


def _player(
    player_id: int,
    role: Role,
    *,
    alive: bool = True,
    sheriff: bool = False,
) -> Player:
    return Player(
        id=player_id,
        name=f"{player_id}号玩家",
        role=role,
        portrait="",
        is_alive=alive,
        is_sheriff=sheriff,
    )


def _find_event_log(game: GameState, event_name: str):
    for log in reversed(game.game_logs):
        if log.data and log.data.get("event") == event_name:
            return log
    raise AssertionError(f"event log not found: {event_name}")


def test_exiled_villager_gets_last_words_before_night():
    players = [
        _player(1, Role.VILLAGER),
        _player(2, Role.VILLAGER),
        _player(3, Role.WOLF),
        _player(4, Role.SEER),
        _player(5, Role.WITCH),
    ]
    game = GameState(
        session_id="exile-last-words",
        day=2,
        phase=GamePhase.DAY_VOTE_RESULT,
        players=players,
        votes={1: 2, 3: 2, 4: 2, 5: 1},
    )

    handler = DayVoteResultHandler(None, game)
    handler.on_enter()
    next_phase = handler.try_advance()

    assert players[1].is_alive is False
    assert next_phase == GamePhase.DAY_LAST_WORDS
    assert game.next_phase_after_last_words == GamePhase.NIGHT_START
    assert game.dead_players == [2]

    game.phase = GamePhase.DAY_LAST_WORDS
    last_words = DayLastWordsHandler(None, game)
    last_words.on_enter()
    assert game.speaking_order == [2]
    assert last_words._on_window_finished() == GamePhase.NIGHT_START
    assert game.next_phase_after_last_words is None


def test_exiled_wolf_king_speaks_last_words_then_shoots():
    players = [
        _player(1, Role.VILLAGER),
        _player(2, Role.WOLF_KING),
        _player(3, Role.WOLF),
        _player(4, Role.SEER),
        _player(5, Role.WITCH),
    ]
    game = GameState(
        session_id="exile-wolf-king",
        day=3,
        phase=GamePhase.DAY_VOTE_RESULT,
        players=players,
        votes={1: 2, 4: 2, 5: 2, 3: 1},
    )

    handler = DayVoteResultHandler(None, game)
    handler.on_enter()
    next_phase = handler.try_advance()

    assert next_phase == GamePhase.DAY_LAST_WORDS
    assert game.next_phase_after_last_words == GamePhase.HUNTER_SKILL
    assert game.next_phase_after_skill == GamePhase.NIGHT_START

    game.phase = GamePhase.DAY_LAST_WORDS
    last_words = DayLastWordsHandler(None, game)
    last_words.on_enter()
    assert last_words._on_window_finished() == GamePhase.HUNTER_SKILL
    assert game.next_phase_after_last_words is None


def test_morning_last_words_still_return_to_day_flow():
    players = [
        _player(1, Role.VILLAGER),
        _player(2, Role.VILLAGER, alive=False),
        _player(3, Role.WOLF),
    ]
    game = GameState(
        session_id="morning-last-words",
        day=2,
        phase=GamePhase.DAY_LAST_WORDS,
        players=players,
        dead_players=[2],
    )

    handler = DayLastWordsHandler(None, game)
    handler.on_enter()
    assert handler._on_window_finished() == GamePhase.DAY_DISCUSS


def test_sheriff_transfer_fallback_tears_badge():
    manager = GameManager()
    dead_sheriff = _player(1, Role.VILLAGER, alive=False, sheriff=True)
    game = GameState(
        session_id="sheriff-fallback",
        day=3,
        phase=GamePhase.SHERIFF_TRANSFER,
        players=[dead_sheriff, _player(2, Role.WOLF), _player(3, Role.SEER)],
        sheriff_id=1,
    )

    action = manager._get_fallback_action(game, dead_sheriff)

    assert action.type == ActionType.VOTE
    assert action.target_id == 0


def test_sheriff_transfer_force_skip_converges_to_torn_badge():
    dead_sheriff = _player(1, Role.VILLAGER, alive=False, sheriff=True)
    game = GameState(
        session_id="sheriff-force-skip",
        day=3,
        phase=GamePhase.SHERIFF_TRANSFER,
        players=[
            dead_sheriff,
            _player(2, Role.WOLF),
            _player(3, Role.SEER),
            _player(4, Role.VILLAGER),
            _player(5, Role.VILLAGER),
        ],
        sheriff_id=1,
        next_phase_after_skill=GamePhase.DAY_START,
    )

    handler = SheriffTransferHandler(None, game)
    handler.on_enter()
    # Simulate a force-skip: the resolution was marked done without any action.
    dead_sheriff.has_acted = True

    next_phase = handler.try_advance()

    assert next_phase == GamePhase.DAY_START
    assert game.sheriff_id is None
    assert dead_sheriff.is_sheriff is False
    torn = _find_event_log(game, "sheriff_badge_torn")
    assert torn.data["previous_sheriff_id"] == 1


def test_wolf_discuss_round_field_survives_discussion_cycle():
    players = [
        _player(1, Role.WOLF),
        _player(2, Role.WOLF_KING),
        _player(3, Role.VILLAGER),
        _player(4, Role.SEER),
    ]
    game = GameState(
        session_id="wolf-round-lifecycle",
        day=1,
        phase=GamePhase.NIGHT_WOLF_DISCUSS,
        players=players,
    )

    handler = NightWolfDiscussHandler(None, game)
    for expected_round in (1, 2, 3):
        handler.on_enter()
        assert game.wolf_discuss_round == expected_round
        for player in players:
            if player.role in (Role.WOLF, Role.WOLF_KING):
                player.has_acted = True
        next_phase = handler.try_advance()

    assert next_phase == GamePhase.NIGHT_WOLF_VOTE
    # The field must stay readable (a deleted pydantic field poisoned every
    # later wolf AI context build with AttributeError).
    assert game.wolf_discuss_round == 0
    assert game.model_copy(deep=True).wolf_discuss_round == 0
