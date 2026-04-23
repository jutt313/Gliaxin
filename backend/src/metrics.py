from __future__ import annotations

from collections import defaultdict
from threading import Lock

_lock = Lock()
_http_counts: dict[tuple[str, str, str], int] = defaultdict(int)
_http_duration_sum: dict[tuple[str, str], float] = defaultdict(float)
_http_duration_count: dict[tuple[str, str], int] = defaultdict(int)
_worker_counts: dict[str, int] = defaultdict(int)


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def record_http_request(method: str, path: str, status: int, duration_ms: float) -> None:
    status_text = str(status)
    key = (method, path, status_text)
    lat_key = (method, path)
    with _lock:
        _http_counts[key] += 1
        _http_duration_sum[lat_key] += duration_ms
        _http_duration_count[lat_key] += 1


def record_worker_outcome(name: str, amount: int = 1) -> None:
    with _lock:
        _worker_counts[name] += amount


def render_metrics(gauges: dict[str, int] | None = None) -> str:
    lines: list[str] = [
        "# HELP gliaxin_http_requests_total Total HTTP requests handled.",
        "# TYPE gliaxin_http_requests_total counter",
    ]
    with _lock:
        for (method, path, status), count in sorted(_http_counts.items()):
            lines.append(
                f'gliaxin_http_requests_total{{method="{_escape(method)}",path="{_escape(path)}",status="{_escape(status)}"}} {count}'
            )

        lines.extend(
            [
                "# HELP gliaxin_http_request_duration_ms_sum Total HTTP request duration in milliseconds.",
                "# TYPE gliaxin_http_request_duration_ms_sum counter",
            ]
        )
        for (method, path), total in sorted(_http_duration_sum.items()):
            lines.append(
                f'gliaxin_http_request_duration_ms_sum{{method="{_escape(method)}",path="{_escape(path)}"}} {total:.3f}'
            )

        lines.extend(
            [
                "# HELP gliaxin_http_request_duration_ms_count Total HTTP request count used for average latency.",
                "# TYPE gliaxin_http_request_duration_ms_count counter",
            ]
        )
        for (method, path), count in sorted(_http_duration_count.items()):
            lines.append(
                f'gliaxin_http_request_duration_ms_count{{method="{_escape(method)}",path="{_escape(path)}"}} {count}'
            )

        lines.extend(
            [
                "# HELP gliaxin_worker_events_total Worker lifecycle counters.",
                "# TYPE gliaxin_worker_events_total counter",
            ]
        )
        for name, count in sorted(_worker_counts.items()):
            lines.append(f'gliaxin_worker_events_total{{event="{_escape(name)}"}} {count}')

    if gauges:
        lines.append("# TYPE gliaxin_runtime_gauge gauge")
        for name, value in sorted(gauges.items()):
            lines.append(f"{name} {value}")

    return "\n".join(lines) + "\n"
