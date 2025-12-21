import pytest
import asyncio
from httpx import AsyncClient
from app.core.event_manager import event_manager
from app.models.events import GameEvent, PhaseChangeEvent
from app.models.game_state import GamePhase
from main import app

@pytest.mark.asyncio
async def test_event_manager_subscription():
    received_events = []
    
    async def callback(event: GameEvent):
        received_events.append(event)
        
    event_manager.subscribe("test_event", callback)
    
    event = GameEvent(event_type="test_event", data={"foo": "bar"})
    await event_manager.publish(event)
    
    # Allow some time for async processing if needed (though publish awaits callbacks)
    assert len(received_events) == 1
    assert received_events[0].data["foo"] == "bar"

@pytest.mark.asyncio
async def test_event_manager_sse_queue():
    player_id = 999
    queue = await event_manager.create_sse_queue(player_id)
    
    event = GameEvent(event_type="test_sse", data={"msg": "hello"})
    await event_manager.push_to_player(player_id, event)
    
    received = await queue.get()
    assert received.event_type == "test_sse"
    assert received.data["msg"] == "hello"
    
    event_manager.remove_sse_queue(player_id)

@pytest.mark.asyncio
async def test_sse_connection():
    # Simplified test: just check if we can connect to the endpoint
    async with AsyncClient(app=app, base_url="http://test") as ac:
        async with ac.stream("GET", "/api/sse/events?player_id=1") as response:
            assert response.status_code == 200
            # We don't iterate to avoid hanging, just check connection established
            pass
