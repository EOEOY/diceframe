"""Short-lived, single-use authorization tickets for browser EventSource."""

from __future__ import annotations

import hashlib
import secrets
import time
from dataclasses import dataclass


@dataclass(frozen=True)
class SseTicket:
    game_key: str
    user_id: str
    expires_at: float


class SseTicketStore:
    def __init__(self, ttl_seconds: int = 30, max_pending: int = 4096) -> None:
        self.ttl_seconds = max(5, int(ttl_seconds))
        self.max_pending = max(16, int(max_pending))
        self._tickets: dict[str, SseTicket] = {}

    @staticmethod
    def _digest(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def _purge(self, now: float) -> None:
        expired = [digest for digest, ticket in self._tickets.items() if ticket.expires_at <= now]
        for digest in expired:
            self._tickets.pop(digest, None)
        while len(self._tickets) >= self.max_pending:
            oldest = min(self._tickets, key=lambda key: self._tickets[key].expires_at)
            self._tickets.pop(oldest, None)

    def issue(self, game_key: str, user_id: str) -> tuple[str, int]:
        now = time.monotonic()
        self._purge(now)
        token = secrets.token_urlsafe(32)
        self._tickets[self._digest(token)] = SseTicket(
            game_key=game_key,
            user_id=user_id,
            expires_at=now + self.ttl_seconds,
        )
        return token, self.ttl_seconds

    def consume(self, token: str, game_key: str) -> SseTicket | None:
        if not token:
            return None
        ticket = self._tickets.pop(self._digest(token), None)
        if not ticket or ticket.expires_at <= time.monotonic() or ticket.game_key != game_key:
            return None
        return ticket
