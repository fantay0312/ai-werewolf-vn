import asyncio
import os

from app.config import reload_config
from app.core.event_manager import event_manager
from app.core.game_manager import GameManager
from app.core.handlers.day_last_words import DayLastWordsHandler
from app.infrastructure.event_store import event_store
from app.infrastructure.game_snapshot_store import GameSnapshotStore
from app.models.events import GameEndEvent, JudgeBroadcastEvent, PhaseChangeEvent
from app.models.action_model import ActionRequest
from app.models.game_state import ActionType, DeathCause, GamePhase, GameState, Player, Role


def _player(player_id: int, role: Role) -> Player:
    return Player(
        id=player_id,
        name=f"{player_id}号玩家",
        role=role,
        portrait="",
        is_human=True,
    )


def _flow_game(phase: GamePhase) -> GameState:
    return GameState(
        session_id=f"flow-{phase.value.lower()}",
        day=1,
        phase=phase,
        players=[
            _player(1, Role.WOLF),
            _player(2, Role.VILLAGER),
            _player(3, Role.VILLAGER),
            _player(4, Role.SEER),
        ],
    )


def test_decisive_day_vote_advances_directly_to_game_end():
    manager = GameManager()
    game = _flow_game(GamePhase.DAY_VOTE)
    game.votes = {1: 1, 2: 1, 3: 1, 4: 1}
    manager.games[game.session_id] = game

    asyncio.run(manager._advance_phase(game, GamePhase.DAY_VOTE_RESULT))

    assert game.winner == "good"
    assert game.phase == GamePhase.GAME_END
    assert not any(log.phase == GamePhase.NIGHT_START for log in game.game_logs)


def test_first_night_kill_reaches_turn_based_last_words():
    manager = GameManager()
    game = _flow_game(GamePhase.NIGHT_GUARD)
    victim = game.players[1]
    victim.killed_by_wolf = True
    game.wolf_kill_target = victim.id
    manager.games[game.session_id] = game

    asyncio.run(manager._advance_phase(game, GamePhase.NIGHT_RESOLVE))

    assert game.phase == GamePhase.DAY_LAST_WORDS
    assert game.speaking_order == [victim.id]
    assert game.current_speaker_index == 0
    assert manager._get_pending_ai_players(game) == []


def test_last_words_ai_scheduler_returns_only_current_speaker():
    manager = GameManager()
    first = _player(1, Role.VILLAGER)
    second = _player(2, Role.SEER)
    first.is_human = False
    second.is_human = False
    first.is_alive = False
    second.is_alive = False
    game = GameState(
        session_id="last-words-ai-order",
        day=2,
        phase=GamePhase.DAY_LAST_WORDS,
        players=[first, second, _player(3, Role.WITCH)],
        dead_players=[second.id, first.id],
    )
    handler = DayLastWordsHandler(manager, game)
    handler.on_enter()

    assert manager._get_pending_ai_players(game) == [first]

    assert handler.process_action(
        ActionRequest(player_id=first.id, type=ActionType.PASS)
    ) is True
    assert manager._get_pending_ai_players(game) == [second]


def test_postponed_sheriff_election_runs_after_first_dawn_last_words():
    victim = _player(1, Role.VILLAGER)
    victim.is_alive = False
    game = GameState(
        session_id="postponed-election-after-last-words",
        day=2,
        phase=GamePhase.DAY_LAST_WORDS,
        players=[victim, _player(2, Role.WOLF), _player(3, Role.SEER)],
        dead_players=[victim.id],
        pending_sheriff_election=True,
    )
    handler = DayLastWordsHandler(None, game)
    handler.on_enter()

    assert handler.process_action(
        ActionRequest(player_id=victim.id, type=ActionType.PASS)
    ) is True
    assert handler.try_advance() == GamePhase.SHERIFF_ELECTION
    assert game.pending_sheriff_election is False


def test_decisive_night_resolution_advances_directly_to_game_end():
    manager = GameManager()
    game = GameState(
        session_id="decisive-night",
        day=1,
        phase=GamePhase.NIGHT_GUARD,
        players=[
            _player(1, Role.WOLF),
            _player(2, Role.VILLAGER),
            _player(3, Role.SEER),
        ],
        wolf_kill_target=2,
    )
    game.players[1].killed_by_wolf = True
    manager.games[game.session_id] = game

    asyncio.run(manager._advance_phase(game, GamePhase.NIGHT_RESOLVE))

    assert game.winner == "wolf"
    assert game.phase == GamePhase.GAME_END


def test_decisive_pk_vote_advances_directly_to_game_end():
    manager = GameManager()
    game = _flow_game(GamePhase.DAY_PK_VOTE)
    game.pk_candidates = [1]
    game.pk_round = 1
    game.pk_votes = {2: 1, 3: 1, 4: 1}
    manager.games[game.session_id] = game

    asyncio.run(manager._advance_phase(game, GamePhase.DAY_PK_RESULT))

    assert game.winner == "good"
    assert game.phase == GamePhase.GAME_END


def test_decisive_hunter_shot_advances_directly_to_game_end():
    manager = GameManager()
    hunter = _player(1, Role.HUNTER)
    hunter.is_alive = False
    hunter.death_cause = DeathCause.VOTE_EXILE
    game = GameState(
        session_id="decisive-shot",
        day=2,
        phase=GamePhase.HUNTER_SKILL,
        players=[
            hunter,
            _player(2, Role.WOLF),
            _player(3, Role.VILLAGER),
            _player(4, Role.SEER),
        ],
        dead_players=[hunter.id],
    )
    manager.games[game.session_id] = game

    success, _ = asyncio.run(manager.process_action(
        game.session_id,
        ActionRequest(player_id=hunter.id, type=ActionType.SHOOT, target_id=2),
    ))

    assert success is True
    assert game.winner == "good"
    assert game.phase == GamePhase.GAME_END


def test_decisive_sheriff_self_explode_advances_directly_to_game_end():
    manager = GameManager()
    game = _flow_game(GamePhase.SHERIFF_ELECTION)
    game.sheriff_candidate_ids = [1]
    manager.games[game.session_id] = game

    asyncio.run(manager._advance_phase(game, GamePhase.SHERIFF_SPEECH))
    success, _ = asyncio.run(manager.process_action(
        game.session_id,
        ActionRequest(player_id=1, type=ActionType.SELF_EXPLODE),
    ))

    assert success is True
    assert game.winner == "good"
    assert game.phase == GamePhase.GAME_END


def test_game_end_is_broadcast_persisted_and_restored(monkeypatch, tmp_path):
    original_env = {
        key: os.environ.get(key)
        for key in ("ENV", "PERSIST_GAMES", "GAME_SNAPSHOT_DIR")
    }
    monkeypatch.setenv("ENV", "test")
    monkeypatch.setenv("PERSIST_GAMES", "true")
    monkeypatch.setenv("GAME_SNAPSHOT_DIR", str(tmp_path))
    reload_config()
    event_store.clear_all()
    event_manager.reset()

    try:
        manager = GameManager()
        game = manager.create_game()
        game.winner = "good"
        queue = asyncio.run(event_manager.create_sse_queue(game.session_id, 0))

        asyncio.run(manager._advance_phase(game, GamePhase.GAME_END))

        delivered_events = []
        while not queue.empty():
            delivered_events.append(queue.get_nowait())

        assert any(isinstance(event, PhaseChangeEvent) for event in delivered_events)
        broadcast = next(event for event in delivered_events if isinstance(event, JudgeBroadcastEvent))
        game_end = next(event for event in delivered_events if isinstance(event, GameEndEvent))
        assert "好人" in broadcast.data["content"]
        assert game_end.data["winner"] == "good"
        snapshot = GameSnapshotStore(tmp_path).load(game.session_id)
        assert snapshot is not None
        assert snapshot.game_state.phase == GamePhase.GAME_END
        assert GameManager().games[game.session_id].phase == GamePhase.GAME_END
    finally:
        event_manager.reset()
        event_store.clear_all()
        for key, value in original_env.items():
            if value is None:
                monkeypatch.delenv(key, raising=False)
            else:
                monkeypatch.setenv(key, value)
        reload_config()
