from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
import math
import re
import threading

DEFAULT_HTTP_HISTOGRAM_BUCKETS: tuple[float, ...] = (
    0.005,
    0.01,
    0.025,
    0.05,
    0.1,
    0.25,
    0.5,
    1.0,
    2.5,
    5.0,
    10.0,
    math.inf,
)

_METRIC_NAME_RE = re.compile(r"[^a-zA-Z0-9_:]")
_MULTI_UNDERSCORE_RE = re.compile(r"_+")


def _normalize_metric_name(name: str) -> str:
    normalized = _METRIC_NAME_RE.sub("_", name.strip()).lower()
    normalized = _MULTI_UNDERSCORE_RE.sub("_", normalized).strip("_")
    if not normalized:
        return "runtime_metric"
    if not re.match(r"[a-zA-Z_:]", normalized[0]):
        normalized = f"metric_{normalized}"
    return normalized


def _normalize_label_name(name: str) -> str:
    normalized = _METRIC_NAME_RE.sub("_", name.strip()).lower()
    normalized = _MULTI_UNDERSCORE_RE.sub("_", normalized).strip("_")
    if not normalized:
        return "label"
    if not re.match(r"[a-zA-Z_:]", normalized[0]):
        normalized = f"label_{normalized}"
    return normalized


def _escape_label_value(value: object) -> str:
    text = str(value)
    return (
        text.replace("\\", r"\\")
        .replace("\n", r"\n")
        .replace('"', r"\"")
    )


def _format_number(value: float | int) -> str:
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, int):
        return str(value)
    if math.isfinite(value) and float(value).is_integer():
        return str(int(value))
    return format(value, ".15g")


def _default_help(metric_type: str, name: str) -> str:
    pretty_name = name.replace("_", " ")
    if metric_type == "counter":
        return f"Total count for {pretty_name}"
    if metric_type == "gauge":
        return f"Current value of {pretty_name}"
    if metric_type == "histogram":
        return f"Observed values for {pretty_name}"
    return f"Collected runtime metric for {pretty_name}"


def _normalize_labels(labels: dict[str, object] | None) -> tuple[tuple[str, str], ...]:
    if not labels:
        return ()
    normalized = tuple(
        sorted(
            ((_normalize_label_name(key), _escape_label_value(value)) for key, value in labels.items()),
            key=lambda item: item[0],
        )
    )
    return normalized


def _render_labels(labels: tuple[tuple[str, str], ...]) -> str:
    if not labels:
        return ""
    parts = [f'{key}="{value}"' for key, value in labels]
    return "{" + ",".join(parts) + "}"


@dataclass
class _HistogramSeries:
    buckets: dict[float, int] = field(default_factory=lambda: defaultdict(int))
    count: int = 0
    sum: float = 0.0


@dataclass
class RuntimeMetricsCollector:
    lock: threading.RLock = field(default_factory=threading.RLock)
    _counter_values: dict[tuple[str, tuple[tuple[str, str], ...]], float] = field(
        default_factory=lambda: defaultdict(float)
    )
    _gauge_values: dict[tuple[str, tuple[tuple[str, str], ...]], float] = field(
        default_factory=dict
    )
    _histogram_values: dict[tuple[str, tuple[tuple[str, str], ...]], _HistogramSeries] = field(
        default_factory=dict
    )
    _metric_types: dict[str, str] = field(default_factory=dict)
    _metric_help: dict[str, str] = field(default_factory=dict)
    _rejected_samples: int = 0

    def clear(self) -> None:
        with self.lock:
            self._counter_values.clear()
            self._gauge_values.clear()
            self._histogram_values.clear()
            self._metric_types.clear()
            self._metric_help.clear()
            self._rejected_samples = 0

    def inc_counter(
        self,
        name: str,
        amount: float = 1.0,
        labels: dict[str, object] | None = None,
        help_text: str | None = None,
    ) -> None:
        metric_name = _normalize_metric_name(name)
        if amount < 0:
            raise ValueError("counter amount must be non-negative")

        labelset = _normalize_labels(labels)
        with self.lock:
            self._register_metric(metric_name, "counter", help_text)
            key = (metric_name, labelset)
            self._counter_values[key] += amount

    def record_business_counter(
        self,
        name: str,
        amount: float = 1.0,
        labels: dict[str, object] | None = None,
        help_text: str | None = None,
    ) -> None:
        self.inc_counter(name=name, amount=amount, labels=labels, help_text=help_text)

    def set_gauge(
        self,
        name: str,
        value: float,
        labels: dict[str, object] | None = None,
        help_text: str | None = None,
    ) -> None:
        metric_name = _normalize_metric_name(name)
        labelset = _normalize_labels(labels)
        with self.lock:
            self._register_metric(metric_name, "gauge", help_text)
            self._gauge_values[(metric_name, labelset)] = float(value)

    def inc_gauge(
        self,
        name: str,
        amount: float = 1.0,
        labels: dict[str, object] | None = None,
        help_text: str | None = None,
    ) -> None:
        metric_name = _normalize_metric_name(name)
        labelset = _normalize_labels(labels)
        with self.lock:
            self._register_metric(metric_name, "gauge", help_text)
            key = (metric_name, labelset)
            self._gauge_values[key] = self._gauge_values.get(key, 0.0) + amount

    def dec_gauge(
        self,
        name: str,
        amount: float = 1.0,
        labels: dict[str, object] | None = None,
        help_text: str | None = None,
    ) -> None:
        self.inc_gauge(name=name, amount=-amount, labels=labels, help_text=help_text)

    def observe_histogram(
        self,
        name: str,
        value: float,
        labels: dict[str, object] | None = None,
        buckets: tuple[float, ...] = DEFAULT_HTTP_HISTOGRAM_BUCKETS,
        help_text: str | None = None,
    ) -> None:
        metric_name = _normalize_metric_name(name)
        labelset = _normalize_labels(labels)
        histogram_buckets = tuple(sorted(buckets))
        if not histogram_buckets:
            raise ValueError("histogram buckets must not be empty")

        with self.lock:
            self._register_metric(metric_name, "histogram", help_text)
            key = (metric_name, labelset)
            series = self._histogram_values.setdefault(key, _HistogramSeries())
            series.count += 1
            series.sum += float(value)
            for bucket in histogram_buckets:
                if value <= bucket:
                    series.buckets[bucket] = series.buckets.get(bucket, 0) + 1
                    break
            else:
                series.buckets[histogram_buckets[-1]] = series.buckets.get(histogram_buckets[-1], 0) + 1

    def record_http_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_seconds: float,
    ) -> None:
        labels = {
            "method": method.upper(),
            "path": path,
            "status": status_code,
        }
        self.inc_counter(
            "http_requests_total",
            labels=labels,
            help_text="Total number of HTTP requests",
        )
        self.observe_histogram(
            "http_request_duration_seconds",
            duration_seconds,
            labels=labels,
            help_text="HTTP request duration in seconds",
        )

    def record_rejected_sample(self) -> None:
        with self.lock:
            self._rejected_samples += 1

    def rejected_samples(self) -> int:
        with self.lock:
            return self._rejected_samples

    def snapshot(self) -> dict[str, object]:
        with self.lock:
            return {
                "counters": dict(self._counter_values),
                "gauges": dict(self._gauge_values),
                "histograms": {
                    key: {
                        "buckets": dict(series.buckets),
                        "count": series.count,
                        "sum": series.sum,
                    }
                    for key, series in self._histogram_values.items()
                },
                "metric_types": dict(self._metric_types),
                "metric_help": dict(self._metric_help),
                "rejected_samples": self._rejected_samples,
            }

    def to_prometheus_text(self) -> str:
        with self.lock:
            lines: list[str] = []

            for metric_name in sorted(self._metric_types):
                metric_type = self._metric_types[metric_name]
                help_text = self._metric_help.get(metric_name, _default_help(metric_type, metric_name))
                lines.append(f"# HELP {metric_name} {help_text}")
                lines.append(f"# TYPE {metric_name} {metric_type}")

                if metric_type == "counter":
                    self._render_counter_lines(metric_name, lines)
                elif metric_type == "gauge":
                    self._render_gauge_lines(metric_name, lines)
                elif metric_type == "histogram":
                    self._render_histogram_lines(metric_name, lines)

            if self._rejected_samples:
                lines.append("# HELP runtime_metrics_rejected_samples_total Rejected metric samples")
                lines.append("# TYPE runtime_metrics_rejected_samples_total counter")
                lines.append(
                    f"runtime_metrics_rejected_samples_total {_format_number(self._rejected_samples)}"
                )

            return "\n".join(lines) + ("\n" if lines else "")

    def _register_metric(self, metric_name: str, metric_type: str, help_text: str | None) -> None:
        existing_type = self._metric_types.get(metric_name)
        if existing_type and existing_type != metric_type:
            raise ValueError(f"metric {metric_name} already registered as {existing_type}")
        self._metric_types[metric_name] = metric_type
        if help_text and metric_name not in self._metric_help:
            self._metric_help[metric_name] = help_text

    def _render_counter_lines(self, metric_name: str, lines: list[str]) -> None:
        for (name, labels), value in sorted(self._counter_values.items()):
            if name != metric_name:
                continue
            lines.append(f"{metric_name}{_render_labels(labels)} {_format_number(value)}")

    def _render_gauge_lines(self, metric_name: str, lines: list[str]) -> None:
        for (name, labels), value in sorted(self._gauge_values.items()):
            if name != metric_name:
                continue
            lines.append(f"{metric_name}{_render_labels(labels)} {_format_number(value)}")

    def _render_histogram_lines(self, metric_name: str, lines: list[str]) -> None:
        histogram_items = [
            (labels, series)
            for (name, labels), series in self._histogram_values.items()
            if name == metric_name
        ]
        for labels, series in sorted(histogram_items, key=lambda item: item[0]):
            cumulative = 0
            ordered_buckets = sorted(series.buckets)
            for bucket in ordered_buckets:
                cumulative += series.buckets[bucket]
                bucket_labels = labels + (("le", "+Inf" if math.isinf(bucket) else _format_number(bucket)),)
                lines.append(f"{metric_name}_bucket{_render_labels(bucket_labels)} {_format_number(cumulative)}")
            lines.append(f"{metric_name}_count{_render_labels(labels)} {_format_number(series.count)}")
            lines.append(f"{metric_name}_sum{_render_labels(labels)} {_format_number(series.sum)}")


runtime_metrics = RuntimeMetricsCollector()


__all__ = [
    "DEFAULT_HTTP_HISTOGRAM_BUCKETS",
    "RuntimeMetricsCollector",
    "runtime_metrics",
]
