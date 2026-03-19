from concurrent.futures import ThreadPoolExecutor

import pytest

from app.infrastructure.runtime_metrics import RuntimeMetricsCollector


def test_counter_updates_are_thread_safe():
    collector = RuntimeMetricsCollector()

    def worker() -> None:
        for _ in range(250):
            collector.inc_counter("games_created_total")

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(worker) for _ in range(8)]
        for future in futures:
            future.result()

    snapshot = collector.snapshot()
    key = ("games_created_total", ())
    assert snapshot["counters"][key] == 2000


def test_gauge_can_be_set_incremented_and_decremented():
    collector = RuntimeMetricsCollector()

    collector.set_gauge("active_sessions", 3)
    collector.inc_gauge("active_sessions")
    collector.dec_gauge("active_sessions", 2)

    snapshot = collector.snapshot()
    key = ("active_sessions", ())
    assert snapshot["gauges"][key] == 2.0


def test_http_metrics_and_prometheus_export_include_core_metric_types():
    collector = RuntimeMetricsCollector()

    collector.record_http_request("get", "/api/game/1", 200, 0.123)
    collector.record_http_request("post", "/api/game/1/action", 400, 0.512)
    collector.record_business_counter(
        "illegal_actions_total",
        labels={"reason": "invalid_target"},
        amount=2,
    )
    collector.set_gauge("queued_jobs", 5)

    text = collector.to_prometheus_text()

    assert "# HELP http_requests_total Total number of HTTP requests" in text
    assert "# TYPE http_requests_total counter" in text
    assert 'http_requests_total{method="GET",path="/api/game/1",status="200"} 1' in text
    assert 'http_request_duration_seconds_bucket{method="GET",path="/api/game/1",status="200",le="0.25"} 1' in text
    assert 'http_request_duration_seconds_count{method="POST",path="/api/game/1/action",status="400"} 1' in text
    assert 'illegal_actions_total{reason="invalid_target"} 2' in text
    assert 'queued_jobs 5' in text


def test_histogram_snapshot_tracks_count_and_sum():
    collector = RuntimeMetricsCollector()

    collector.observe_histogram("action_latency_seconds", 0.2)
    collector.observe_histogram("action_latency_seconds", 1.7)

    snapshot = collector.snapshot()
    key = ("action_latency_seconds", ())
    histogram = snapshot["histograms"][key]
    assert histogram["count"] == 2
    assert histogram["sum"] == pytest.approx(1.9)
    assert histogram["buckets"][0.25] == 1
    assert histogram["buckets"][2.5] == 1
