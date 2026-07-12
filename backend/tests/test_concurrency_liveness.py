import asyncio

from app.ai.agent import AIAgent
from app.core.game_manager import GameManager, game_manager
from app.models.action_model import ActionRequest
from app.models.game_state import ActionType, GamePhase, GameState, Player, Role
from main import app, lifespan


def _player(player_id: int, role: Role, *, human: bool = False) -> Player:
    return Player(
        id=player_id,
        name=f"{player_id}号玩家",
        role=role,
        portrait="",
        is_human=human,
    )


def test_process_action_waits_for_session_mutation_lock():
    manager = GameManager()
    human = _player(1, Role.VILLAGER, human=True)
    game = GameState(
        session_id="serialized-human-action",
        day=1,
        phase=GamePhase.GAME_START,
        players=[human],
    )
    manager.games[game.session_id] = game
    lock = manager.ai_locks.setdefault(game.session_id, asyncio.Lock())

    async def runner():
        await lock.acquire()
        action_task = asyncio.create_task(manager.process_action(
            game.session_id,
            ActionRequest(player_id=human.id, type=ActionType.CONFIRM),
        ))
        await asyncio.sleep(0)
        try:
            assert action_task.done() is False
        finally:
            lock.release()
        success, error = await action_task
        assert success is True, error

    asyncio.run(runner())


def test_ai_decision_does_not_hold_session_mutation_lock(monkeypatch):
    manager = GameManager()
    ai_player = _player(1, Role.VILLAGER)
    game = GameState(
        session_id="unlocked-ai-decision",
        day=2,
        phase=GamePhase.DAY_VOTE,
        players=[ai_player, _player(2, Role.WOLF, human=True), _player(3, Role.SEER, human=True)],
    )
    manager.games[game.session_id] = game
    manager.ai_locks[game.session_id] = asyncio.Lock()
    decision_started = asyncio.Event()
    release_decision = asyncio.Event()

    async def blocked_decision(self, current_game):
        decision_started.set()
        await release_decision.wait()
        return ActionRequest(player_id=ai_player.id, type=ActionType.VOTE, target_id=2)

    monkeypatch.setattr(AIAgent, "decide_action", blocked_decision)

    async def runner():
        task = asyncio.create_task(manager.trigger_ai_actions(game.session_id))
        await decision_started.wait()
        assert manager.ai_locks[game.session_id].locked() is False
        release_decision.set()
        await task

    asyncio.run(runner())


def test_stale_ai_action_is_discarded_after_concurrent_human_advance(monkeypatch):
    manager = GameManager()
    human = _player(1, Role.VILLAGER, human=True)
    ai_player = _player(2, Role.WOLF)
    game = GameState(
        session_id="stale-ai-action",
        day=1,
        phase=GamePhase.GAME_START,
        players=[human, ai_player],
    )
    manager.games[game.session_id] = game
    decision_started = asyncio.Event()
    release_decision = asyncio.Event()

    async def delayed_pass(self, current_game):
        decision_started.set()
        await release_decision.wait()
        return ActionRequest(player_id=ai_player.id, type=ActionType.PASS)

    monkeypatch.setattr(AIAgent, "decide_action", delayed_pass)

    async def runner():
        ai_task = asyncio.create_task(manager.trigger_ai_actions(game.session_id))
        await decision_started.wait()
        success, error = await manager.process_action(
            game.session_id,
            ActionRequest(player_id=human.id, type=ActionType.CONFIRM),
        )
        assert success is True, error
        assert game.phase == GamePhase.SHERIFF_ELECTION
        ai_player.is_human = True
        release_decision.set()
        await ai_task

    asyncio.run(runner())

    assert ai_player.has_acted is False
    assert not any(
        log.player_id == ai_player.id and log.phase == GamePhase.SHERIFF_ELECTION
        for log in game.game_logs
    )


def test_forced_ai_skip_advances_speech_window(monkeypatch):
    manager = GameManager()
    ai_player = _player(1, Role.VILLAGER)
    human = _player(2, Role.SEER, human=True)
    game = GameState(
        session_id="forced-speech-skip",
        day=2,
        phase=GamePhase.DAY_DISCUSS,
        players=[ai_player, human, _player(3, Role.WOLF, human=True)],
        speaking_order=[ai_player.id, human.id],
        current_speaker_index=0,
    )
    human.has_acted = True
    manager.games[game.session_id] = game
    manager.ai_locks[game.session_id] = asyncio.Lock()

    async def invalid_decision(self, current_game):
        return ActionRequest(player_id=ai_player.id, type=ActionType.KILL, target_id=2)

    monkeypatch.setattr(AIAgent, "decide_action", invalid_decision)
    monkeypatch.setattr(
        manager,
        "_get_fallback_action",
        lambda current_game, player: ActionRequest(
            player_id=player.id,
            type=ActionType.KILL,
            target_id=2,
        ),
    )

    asyncio.run(manager.trigger_ai_actions(game.session_id))

    assert game.current_speaker_index == 1
    assert human.has_acted is False
    assert any(
        log.data and log.data.get("event") == "speech_window_force_advanced"
        for log in game.game_logs
    )


def test_lifespan_resumes_ai_for_loaded_sessions(monkeypatch):
    resumed_sessions = []

    async def record_resume(session_id: str):
        resumed_sessions.append(session_id)

    monkeypatch.setattr(game_manager, "restore_persisted_games", lambda: 2)
    monkeypatch.setattr(game_manager, "games", {"restored-a": object(), "restored-b": object()})
    monkeypatch.setattr(game_manager, "run_maintenance", lambda: None)
    monkeypatch.setattr(game_manager, "persist_all_games", lambda: 0)
    monkeypatch.setattr(game_manager, "trigger_ai_actions", record_resume)

    async def runner():
        async with lifespan(app):
            await asyncio.sleep(0)
            assert sorted(resumed_sessions) == ["restored-a", "restored-b"]

    asyncio.run(runner())
