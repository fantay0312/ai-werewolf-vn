import asyncio

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sse_starlette.sse import EventSourceResponse
from starlette.requests import Request

from app.config import Environment, ServerConfig
from app.core.event_manager import SSE_QUEUE_CLOSED, EventManager, event_manager
from app.core.game_manager import game_manager
from app.domain.events.base import DomainEvent, VisibilityScope
from app.domain.events.gameplay import player_action_received
from app.interfaces.presenters.event_presenter import EventPresenter
from app.infrastructure.runtime_metrics import runtime_metrics
from app.infrastructure.sse_ticket_store import SSETicketStore, sse_ticket_store
from app.models.events import GameEvent
from app.models.game_state import ActionType, GamePhase, GameState, Player, Role
from app.routes.sse import heartbeat_sse_frame, sse_endpoint
from main import app


client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_event_manager():
    event_manager.reset()
    sse_ticket_store.reset()
    yield
    event_manager.reset()
    sse_ticket_store.reset()


def test_event_manager_subscription():
    received_events = []

    async def callback(event):
        received_events.append(event)

    event_manager.subscribe("test_event", callback)

    async def runner():
        event = GameEvent(
            event_type="test_event",
            data={"session_id": "session-subscription", "foo": "bar"},
        )
        await event_manager.publish(event)

    asyncio.run(runner())

    assert len(received_events) == 1
    assert received_events[0].data["foo"] == "bar"


def test_event_manager_isolates_sessions_for_public_events():
    async def runner():
        queue_a = await event_manager.create_sse_queue("session-a", 0)
        queue_b = await event_manager.create_sse_queue("session-b", 0)

        event = GameEvent(
            event_type="judge_broadcast",
            data={"session_id": "session-a", "content": "hello"},
        )
        await event_manager.publish(event)

        received = await asyncio.wait_for(queue_a.get(), timeout=0.2)
        assert received.event_type == "judge_broadcast"

        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(queue_b.get(), timeout=0.1)

    asyncio.run(runner())


def test_event_manager_routes_private_domain_event_only_to_actor_viewer():
    presenter = EventPresenter()

    async def runner():
        public_queue = await event_manager.create_sse_queue("session-private", 0)
        actor_queue = await event_manager.create_sse_queue("session-private", 7)
        target_queue = await event_manager.create_sse_queue("session-private", 8)

        event = DomainEvent(
            name="player_action_received",
            game_id="session-private",
            day=1,
            phase=GamePhase.NIGHT_WOLF_VOTE,
            payload={"action_type": "kill", "note": "secret"},
            visibility=VisibilityScope.PRIVATE,
            actor_id=7,
            target_id=8,
        )

        await event_manager.publish(event)

        received = await asyncio.wait_for(actor_queue.get(), timeout=0.2)
        presented = presenter.present(received, viewer_id=7)
        assert presented["event_type"] == "player_action_received"
        assert presented["visibility"] == "private"
        assert presented["data"]["note"] == "secret"

        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(public_queue.get(), timeout=0.1)
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(target_queue.get(), timeout=0.1)

    asyncio.run(runner())


def test_player_action_event_marks_night_and_live_vote_actions_actor_private():
    game = GameState(
        session_id="covert-actions",
        day=1,
        phase=GamePhase.NIGHT_WOLF_VOTE,
        players=[
            Player(id=1, name="Wolf", role=Role.WOLF, portrait=""),
            Player(id=2, name="Villager", role=Role.VILLAGER, portrait=""),
        ],
    )

    night_event = player_action_received(
        game,
        actor_id=1,
        action_type=ActionType.KILL,
        target_id=2,
        source="ai",
    )
    game.phase = GamePhase.DAY_VOTE
    vote_event = player_action_received(
        game,
        actor_id=2,
        action_type=ActionType.VOTE,
        target_id=1,
        source="human",
    )
    game.phase = GamePhase.DAY_DISCUSS
    speech_event = player_action_received(
        game,
        actor_id=2,
        action_type=ActionType.SPEECH,
        target_id=None,
        source="human",
    )

    assert night_event.visibility == VisibilityScope.PRIVATE
    assert vote_event.visibility == VisibilityScope.PRIVATE
    assert speech_event.visibility == VisibilityScope.PUBLIC


def test_sse_queue_is_bounded_and_drops_oldest(caplog):
    manager = EventManager(queue_capacity=2)
    runtime_metrics.clear()

    async def runner():
        queue = await manager.create_sse_queue("bounded-session", 0)
        for sequence in range(3):
            await manager.publish(GameEvent(
                event_type="state_update",
                data={"session_id": "bounded-session", "sequence": sequence},
            ))
        assert queue.maxsize == 2
        assert [queue.get_nowait().data["sequence"] for _ in range(2)] == [1, 2]

    with caplog.at_level("WARNING"):
        asyncio.run(runner())

    assert "Dropped oldest SSE event" in caplog.text
    assert 'sse_events_dropped_total{reason="queue_full"} 1' in runtime_metrics.to_prometheus_text()


def test_sse_queue_cap_evicts_and_closes_oldest_viewer_stream():
    manager = EventManager(queue_capacity=2)

    async def runner():
        first = await manager.create_sse_queue("viewer-cap", 7)
        second = await manager.create_sse_queue("viewer-cap", 7)
        third = await manager.create_sse_queue("viewer-cap", 7)

        assert first.get_nowait() is SSE_QUEUE_CLOSED
        await manager.publish(GameEvent(
            event_type="state_update",
            data={"session_id": "viewer-cap"},
        ))
        assert (await second.get()).event_type == "state_update"
        assert (await third.get()).event_type == "state_update"

    asyncio.run(runner())


def test_sse_heartbeat_is_a_browser_visible_data_event():
    frame = heartbeat_sse_frame()

    assert "comment" not in frame
    assert '"event_type": "heartbeat"' in frame["data"]
    assert '"schema": "system"' in frame["data"]


def test_sse_heartbeat_interval_defaults_and_reads_environment(monkeypatch):
    monkeypatch.delenv("SSE_HEARTBEAT_SECONDS", raising=False)
    assert ServerConfig.from_env(Environment.TEST).sse_heartbeat_seconds == 15

    monkeypatch.setenv("SSE_HEARTBEAT_SECONDS", "9")
    assert ServerConfig.from_env(Environment.TEST).sse_heartbeat_seconds == 9


def test_sse_ticket_ttl_is_capped_at_sixty_seconds():
    store = SSETicketStore()

    ticket, expires_in = store.issue("ttl-session", 1, ttl_seconds=999)

    assert ticket
    assert expires_in == 60


def test_event_presenter_emits_unnamed_sse_with_domain_id():
    presenter = EventPresenter()
    event = DomainEvent(
        name="phase_entered",
        game_id="unnamed-sse",
        day=2,
        phase=GamePhase.DAY_START,
        payload={"current_phase": GamePhase.DAY_START.value},
    )

    rendered = presenter.to_sse(event, viewer_id=1)

    assert "event" not in rendered
    assert rendered["id"] == event.event_id
    assert '"event_type": "phase_entered"' in rendered["data"]


def _build_request() -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/api/sse/events",
            "headers": [],
            "query_string": b"",
        }
    )


def test_sse_public_subscription_requires_session_but_not_token():
    game = game_manager.create_game()

    async def runner():
        response = await sse_endpoint(
            _build_request(),
            session_id=game.session_id,
            viewer_id=None,
            player_id=None,
            x_player_token=None,
        )
        assert isinstance(response, EventSourceResponse)

    asyncio.run(runner())


def test_sse_private_subscription_rejects_missing_or_invalid_token():
    game = game_manager.create_game()
    human_player = next(player for player in game.players if player.is_human)

    async def runner():
        with pytest.raises(HTTPException) as missing_token_error:
            await sse_endpoint(
                _build_request(),
                session_id=game.session_id,
                viewer_id=human_player.id,
                player_id=None,
                x_player_token=None,
            )
        assert missing_token_error.value.status_code == 403

        with pytest.raises(HTTPException) as invalid_token_error:
            await sse_endpoint(
                _build_request(),
                session_id=game.session_id,
                viewer_id=human_player.id,
                player_id=None,
                x_player_token="invalid-token",
            )
        assert invalid_token_error.value.status_code == 403

    asyncio.run(runner())


def test_sse_private_subscription_accepts_matching_token():
    game = game_manager.create_game()
    human_player = next(player for player in game.players if player.is_human)
    token = game_manager.get_player_token(game.session_id)

    async def runner():
        response = await sse_endpoint(
            _build_request(),
            session_id=game.session_id,
            viewer_id=human_player.id,
            player_id=None,
            x_player_token=token,
        )
        assert isinstance(response, EventSourceResponse)

    asyncio.run(runner())


def test_sse_ticket_authenticates_once_without_browser_header():
    game = game_manager.create_game()
    human_player = next(player for player in game.players if player.is_human)
    token = game_manager.get_player_token(game.session_id)
    ticket_response = client.post(
        f"/api/sse/ticket?session_id={game.session_id}",
        headers={"X-Player-Token": token},
    )

    assert ticket_response.status_code == 200
    payload = ticket_response.json()
    assert isinstance(payload["ticket"], str)
    assert 1 <= payload["expires_in"] <= 60

    async def runner():
        response = await sse_endpoint(
            _build_request(),
            session_id=game.session_id,
            viewer_id=human_player.id,
            player_id=None,
            ticket=payload["ticket"],
            x_player_token=None,
        )
        assert isinstance(response, EventSourceResponse)

        with pytest.raises(HTTPException) as reused_ticket_error:
            await sse_endpoint(
                _build_request(),
                session_id=game.session_id,
                viewer_id=human_player.id,
                player_id=None,
                ticket=payload["ticket"],
                x_player_token=None,
            )
        assert reused_ticket_error.value.status_code == 403

    asyncio.run(runner())
