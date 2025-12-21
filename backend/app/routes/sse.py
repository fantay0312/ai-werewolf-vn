from fastapi import APIRouter, Request, Query
from sse_starlette.sse import EventSourceResponse
from app.core.event_manager import event_manager
import logging
import asyncio
import json

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/events")
async def sse_endpoint(request: Request, player_id: int = Query(0)):
    """
    SSE endpoint for game events.
    player_id=0 indicates an observer or public view.
    """
    logger.info(f"Client connected to SSE: player_id={player_id}")
    queue = await event_manager.create_sse_queue(player_id)
    
    async def event_generator():
        try:
            while True:
                # Check for disconnection
                if await request.is_disconnected():
                    logger.info(f"Client disconnected: player_id={player_id}")
                    break
                
                try:
                    # Wait for event with timeout to allow checking disconnection
                    event = await asyncio.wait_for(queue.get(), timeout=1.0)
                    
                    # Format event for SSE
                    yield {
                        "event": event.event_type,
                        "data": json.dumps(event.data)
                    }
                except asyncio.TimeoutError:
                    # Send keep-alive comment
                    yield {"comment": "keep-alive"}
                    
        except asyncio.CancelledError:
            logger.info(f"SSE stream cancelled: player_id={player_id}")
        finally:
            event_manager.remove_sse_queue(player_id)
            
    return EventSourceResponse(event_generator())
