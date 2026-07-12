import asyncio
import logging

from fastapi import APIRouter, Header, HTTPException, Query, Request
from sse_starlette.sse import EventSourceResponse

from app.core.event_manager import event_manager
from app.core.game_manager import game_manager
from app.config import get_server_config
from app.infrastructure.sse_ticket_store import sse_ticket_store
from app.interfaces.presenters.event_presenter import EventPresenter
from app.security import PLAYER_TOKEN_HEADER

router = APIRouter()
logger = logging.getLogger(__name__)
event_presenter = EventPresenter()


@router.post("/ticket")
async def create_sse_ticket(
    session_id: str = Query(...),
    viewer_id: int | None = Query(default=None),
    x_player_token: str | None = Header(default=None, alias=PLAYER_TOKEN_HEADER),
):
    if game_manager.get_game(session_id) is None:
        raise HTTPException(status_code=404, detail="Game not found")

    authenticated_viewer_id = game_manager.authenticate_player(session_id, x_player_token)
    if authenticated_viewer_id is None:
        raise HTTPException(status_code=403, detail="玩家认证失败")
    if viewer_id is not None and viewer_id != authenticated_viewer_id:
        raise HTTPException(status_code=403, detail="玩家认证失败")

    ticket, expires_in = sse_ticket_store.issue(
        session_id,
        authenticated_viewer_id,
        get_server_config().sse_ticket_ttl_seconds,
    )
    return {"ticket": ticket, "expires_in": expires_in}


@router.get("/events")
async def sse_endpoint(
    request: Request,
    session_id: str = Query(...),
    viewer_id: int | None = Query(default=None),
    player_id: int | None = Query(default=None),
    ticket: str | None = None,
    x_player_token: str | None = Header(default=None, alias=PLAYER_TOKEN_HEADER),
):
    """
    SSE endpoint for game events.

    - `session_id` 必填，避免跨局串流。
    - `viewer_id` 为新参数。
    - `player_id` 仅作为旧参数兼容别名使用。
    """
    game = game_manager.get_game(session_id)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    header_viewer_id = game_manager.authenticate_player(session_id, x_player_token)
    if x_player_token is not None and header_viewer_id is None:
        raise HTTPException(status_code=403, detail="玩家认证失败")

    ticket_viewer_id = None
    if ticket is not None:
        ticket_viewer_id = sse_ticket_store.consume(ticket, session_id)
        if ticket_viewer_id is None:
            raise HTTPException(status_code=403, detail="SSE ticket无效或已过期")
        if header_viewer_id is not None and header_viewer_id != ticket_viewer_id:
            raise HTTPException(status_code=403, detail="玩家认证失败")

    authenticated_viewer_id = ticket_viewer_id or header_viewer_id

    requested_viewer_id = viewer_id if viewer_id is not None else player_id
    if requested_viewer_id is None:
        resolved_viewer_id = authenticated_viewer_id or 0
    elif requested_viewer_id == 0:
        resolved_viewer_id = 0
    else:
        if authenticated_viewer_id != requested_viewer_id:
            raise HTTPException(status_code=403, detail="玩家认证失败")
        resolved_viewer_id = requested_viewer_id

    logger.info(
        "Client connected to SSE: session_id=%s viewer_id=%s",
        session_id,
        resolved_viewer_id,
    )
    queue = await event_manager.create_sse_queue(session_id, resolved_viewer_id)

    async def event_generator():
        try:
            while True:
                if await request.is_disconnected():
                    logger.info(
                        "Client disconnected from SSE: session_id=%s viewer_id=%s",
                        session_id,
                        resolved_viewer_id,
                    )
                    break

                try:
                    event = await asyncio.wait_for(queue.get(), timeout=1.0)
                    yield event_presenter.to_sse(
                        event,
                        session_id=session_id,
                        viewer_id=resolved_viewer_id,
                    )
                except asyncio.TimeoutError:
                    yield {"comment": "keep-alive"}
        except asyncio.CancelledError:
            logger.info(
                "SSE stream cancelled: session_id=%s viewer_id=%s",
                session_id,
                resolved_viewer_id,
            )
        finally:
            event_manager.remove_sse_queue(session_id, resolved_viewer_id, queue)

    return EventSourceResponse(event_generator())
