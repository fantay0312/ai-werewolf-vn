from __future__ import annotations

import secrets
import threading
import time
from dataclasses import dataclass


MAX_TICKET_TTL_SECONDS = 60


@dataclass(frozen=True)
class SSETicket:
    session_id: str
    viewer_id: int
    expires_at: float


class SSETicketStore:
    """Short-lived, single-use credentials for browser EventSource clients."""

    def __init__(self):
        self._tickets: dict[str, SSETicket] = {}
        self._lock = threading.Lock()

    def issue(self, session_id: str, viewer_id: int, ttl_seconds: int) -> tuple[str, int]:
        ttl = max(1, min(MAX_TICKET_TTL_SECONDS, int(ttl_seconds)))
        now = time.monotonic()
        with self._lock:
            self._remove_expired(now)
            self._remove_viewer_ticket(session_id, viewer_id)
            token = secrets.token_urlsafe(32)
            self._tickets[token] = SSETicket(
                session_id=session_id,
                viewer_id=viewer_id,
                expires_at=now + ttl,
            )
        return token, ttl

    def consume(self, token: str, session_id: str) -> int | None:
        now = time.monotonic()
        with self._lock:
            ticket = self._tickets.pop(token, None)
        if ticket is None or ticket.expires_at <= now or ticket.session_id != session_id:
            return None
        return ticket.viewer_id

    def reset(self) -> None:
        with self._lock:
            self._tickets.clear()

    def _remove_expired(self, now: float) -> None:
        expired = [token for token, ticket in self._tickets.items() if ticket.expires_at <= now]
        for token in expired:
            self._tickets.pop(token, None)

    def _remove_viewer_ticket(self, session_id: str, viewer_id: int) -> None:
        matching = [
            token
            for token, ticket in self._tickets.items()
            if ticket.session_id == session_id and ticket.viewer_id == viewer_id
        ]
        for token in matching:
            self._tickets.pop(token, None)


sse_ticket_store = SSETicketStore()
