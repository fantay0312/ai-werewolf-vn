from __future__ import annotations

from threading import Barrier, Lock, Thread

from app.infrastructure.rate_limiter import RateLimiter


def test_rate_limiter_allows_until_limit_then_denies():
    current_time = [100.0]
    limiter = RateLimiter(clock=lambda: current_time[0])

    assert limiter.allow("api", "alice", 10, 2) is True
    assert limiter.allow("api", "alice", 10, 2) is True
    assert limiter.allow("api", "alice", 10, 2) is False

    stats = limiter.snapshot("api", "alice", 10, 2)
    assert len(stats) == 1

    stat = stats[0]
    assert stat.bucket == "api"
    assert stat.key == "alice"
    assert stat.window_seconds == 10.0
    assert stat.limit == 2
    assert stat.attempts == 3
    assert stat.allowed == 2
    assert stat.denied == 1
    assert stat.active == 2
    assert stat.remaining == 0


def test_rate_limiter_window_slides_and_recovers_capacity():
    current_time = [0.0]
    limiter = RateLimiter(clock=lambda: current_time[0])

    assert limiter.allow("api", "alice", 10, 2) is True
    assert limiter.allow("api", "alice", 10, 2) is True
    assert limiter.allow("api", "alice", 10, 2) is False

    current_time[0] = 10.01
    assert limiter.allow("api", "alice", 10, 2) is True

    stat = limiter.snapshot("api", "alice", 10, 2)[0]
    assert stat.attempts == 4
    assert stat.allowed == 3
    assert stat.denied == 1
    assert stat.active == 1
    assert stat.remaining == 1


def test_rate_limiter_keeps_buckets_and_keys_isolated():
    current_time = [50.0]
    limiter = RateLimiter(clock=lambda: current_time[0])

    assert limiter.allow("chat", "alice", 30, 1) is True
    assert limiter.allow("chat", "alice", 30, 1) is False
    assert limiter.allow("admin", "alice", 30, 1) is True
    assert limiter.allow("chat", "bob", 30, 1) is True

    chat_alice = limiter.snapshot("chat", "alice", 30, 1)[0]
    admin_alice = limiter.snapshot("admin", "alice", 30, 1)[0]
    chat_bob = limiter.snapshot("chat", "bob", 30, 1)[0]

    assert chat_alice.denied == 1
    assert chat_alice.allowed == 1
    assert admin_alice.allowed == 1
    assert admin_alice.denied == 0
    assert chat_bob.allowed == 1
    assert chat_bob.denied == 0


def test_rate_limiter_is_thread_safe_under_contention():
    limiter = RateLimiter()
    worker_count = 20
    barrier = Barrier(worker_count)
    results: list[bool] = []
    results_lock = Lock()

    def worker() -> None:
        barrier.wait()
        allowed = limiter.allow("burst", "shared", 60, 5)
        with results_lock:
            results.append(allowed)

    threads = [Thread(target=worker) for _ in range(worker_count)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(results) == worker_count
    assert sum(results) == 5

    stat = limiter.snapshot("burst", "shared", 60, 5)[0]
    assert stat.allowed == 5
    assert stat.denied == 15
    assert stat.active == 5
