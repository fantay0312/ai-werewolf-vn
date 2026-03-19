import asyncio

import pytest
from fastapi import HTTPException
from sse_starlette.sse import EventSourceResponse
from starlette.requests import Request

from app.core.event_manager import event_manager
from app.core.game_manager import game_manager
from app.domain.events.base import DomainEvent, VisibilityScope
from app.interfaces.presenters.event_presenter import EventPresenter
from app.models.events import GameEvent
from app.models.game_state import GamePhase
from app.routes.sse import sse_endpoint


@pytest.fixture(autouse=True)
def reset_event_manager():
    event_manager.reset()
    yield
    event_manager.reset()


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


def test_event_manager_routes_private_domain_event_only_to_target_viewer():
    presenter = EventPresenter()

    async def runner():
        public_queue = await event_manager.create_sse_queue("session-private", 0)
        private_queue = await event_manager.create_sse_queue("session-private", 7)

        event = DomainEvent(
            name="player_action_received",
            game_id="session-private",
            day=1,
            phase=GamePhase.NIGHT_WOLF_VOTE,
            payload={"action_type": "kill", "note": "secret"},
            visibility=VisibilityScope.PRIVATE,
            actor_id=7,
        )

        await event_manager.publish(event)

        received = await asyncio.wait_for(private_queue.get(), timeout=0.2)
        presented = presenter.present(received, viewer_id=7)
        assert presented["event_type"] == "player_action_received"
        assert presented["visibility"] == "private"
        assert presented["data"]["note"] == "secret"

        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(public_queue.get(), timeout=0.1)

    asyncio.run(runner())


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
