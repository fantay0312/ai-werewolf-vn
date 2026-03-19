from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from threading import RLock
from time import monotonic
from typing import Callable, Deque


@dataclass(frozen=True, slots=True)
class RateLimitStats:
    bucket: str
    key: str
    window_seconds: float
    limit: int
    attempts: int
    allowed: int
    denied: int
    active: int
    remaining: int


@dataclass(slots=True)
class _RuleState:
    timestamps: Deque[float]
    attempts: int = 0
    allowed: int = 0
    denied: int = 0


class RateLimiter:
    """Thread-safe in-memory sliding-window rate limiter."""

    def __init__(self, clock: Callable[[], float] | None = None) -> None:
        self._clock = clock or monotonic
        self._lock = RLock()
        self._states: dict[tuple[str, str, float, int], _RuleState] = {}

    def allow(self, bucket: str, key: str, window_seconds: float, limit: int) -> bool:
        rule_id = self._normalize_rule_id(bucket, key, window_seconds, limit)
        now = self._clock()

        with self._lock:
            state = self._states.setdefault(rule_id, _RuleState(timestamps=deque()))
            state.attempts += 1

            if rule_id[2] <= 0 or rule_id[3] <= 0:
                state.denied += 1
                return False

            self._prune(state, now, rule_id[2])
            if len(state.timestamps) >= rule_id[3]:
                state.denied += 1
                return False

            state.timestamps.append(now)
            state.allowed += 1
            return True

    def clear(self) -> None:
        with self._lock:
            self._states.clear()

    def retry_after(self, bucket: str, key: str, window_seconds: float, limit: int) -> float:
        rule_id = self._normalize_rule_id(bucket, key, window_seconds, limit)
        now = self._clock()

        with self._lock:
            state = self._states.get(rule_id)
            if state is None:
                return 0.0
            self._prune(state, now, rule_id[2])
            if len(state.timestamps) < rule_id[3] or not state.timestamps:
                return 0.0
            return max(0.0, state.timestamps[0] + rule_id[2] - now)

    def snapshot(
        self,
        bucket: str | None = None,
        key: str | None = None,
        window_seconds: float | None = None,
        limit: int | None = None,
    ) -> list[RateLimitStats]:
        with self._lock:
            now = self._clock()
            stats: list[RateLimitStats] = []

            for rule_id, state in self._states.items():
                if not self._matches(rule_id, bucket, key, window_seconds, limit):
                    continue

                self._prune(state, now, rule_id[2])
                active = len(state.timestamps)
                remaining = max(0, rule_id[3] - active)
                stats.append(
                    RateLimitStats(
                        bucket=rule_id[0],
                        key=rule_id[1],
                        window_seconds=rule_id[2],
                        limit=rule_id[3],
                        attempts=state.attempts,
                        allowed=state.allowed,
                        denied=state.denied,
                        active=active,
                        remaining=remaining,
                    )
                )

            stats.sort(key=lambda item: (item.bucket, item.key, item.window_seconds, item.limit))
            return stats

    def clear(self) -> None:
        with self._lock:
            self._states.clear()

    def _normalize_rule_id(
        self,
        bucket: str,
        key: str,
        window_seconds: float,
        limit: int,
    ) -> tuple[str, str, float, int]:
        return (str(bucket), str(key), float(window_seconds), int(limit))

    def _matches(
        self,
        rule_id: tuple[str, str, float, int],
        bucket: str | None,
        key: str | None,
        window_seconds: float | None,
        limit: int | None,
    ) -> bool:
        if bucket is not None and rule_id[0] != bucket:
            return False
        if key is not None and rule_id[1] != key:
            return False
        if window_seconds is not None and rule_id[2] != float(window_seconds):
            return False
        if limit is not None and rule_id[3] != int(limit):
            return False
        return True

    def _prune(self, state: _RuleState, now: float, window_seconds: float) -> None:
        cutoff = now - window_seconds
        while state.timestamps and state.timestamps[0] <= cutoff:
            state.timestamps.popleft()


__all__ = ["RateLimitStats", "RateLimiter"]
