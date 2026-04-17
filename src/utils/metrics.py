from __future__ import annotations

from contextlib import contextmanager
from time import perf_counter
from typing import Iterator

import httpx
from fastapi import FastAPI
from prometheus_client import Counter, Gauge, Histogram
from prometheus_fastapi_instrumentator import Instrumentator

_API_LATENCY_BUCKETS = (
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
    30.0,
    60.0,
)

_PARSER_LATENCY_BUCKETS = (
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
    20.0,
    40.0,
    60.0,
)

_TEXT_SIZE_BUCKETS = (
    50.0,
    100.0,
    250.0,
    500.0,
    750.0,
    1000.0,
    1500.0,
    2000.0,
    3000.0,
    4000.0,
)


API_REQUESTS_TOTAL = Counter(
    "hr_parser_api_requests_total",
    "Total API requests handled by the HR parser service.",
    ("route", "method", "status_code"),
)

API_REQUEST_DURATION_SECONDS = Histogram(
    "hr_parser_api_request_duration_seconds",
    "End-to-end HTTP request latency in seconds.",
    ("route", "method", "status_code"),
    buckets=_API_LATENCY_BUCKETS,
)

API_IN_PROGRESS = Gauge(
    "hr_parser_api_in_progress_requests",
    "Current number of in-flight API requests.",
    ("route", "method"),
)

PARSER_REQUESTS_TOTAL = Counter(
    "hr_parser_parse_requests_total",
    "Total number of parser requests by final outcome.",
    ("outcome",),
)

PARSER_DURATION_SECONDS = Histogram(
    "hr_parser_parse_duration_seconds",
    "Job description parsing latency in seconds.",
    ("outcome",),
    buckets=_PARSER_LATENCY_BUCKETS,
)

FALLBACKS_TOTAL = Counter(
    "hr_parser_fallback_total",
    "Number of times fallback payload was returned.",
    ("reason",),
)

JOB_DESCRIPTION_SIZE_CHARS = Histogram(
    "hr_parser_job_description_size_chars",
    "Input job description size in characters.",
    buckets=_TEXT_SIZE_BUCKETS,
)

VLLM_REQUESTS_TOTAL = Counter(
    "hr_parser_vllm_requests_total",
    "Total requests issued to vLLM backend by outcome.",
    ("model", "outcome"),
)

VLLM_REQUEST_DURATION_SECONDS = Histogram(
    "hr_parser_vllm_request_duration_seconds",
    "vLLM backend request latency in seconds.",
    ("model", "outcome"),
    buckets=_PARSER_LATENCY_BUCKETS,
)

VLLM_ERRORS_TOTAL = Counter(
    "hr_parser_vllm_errors_total",
    "Total vLLM errors grouped by normalized error type and status class.",
    ("model", "error_type", "status_class"),
)


def _norm_route(route: str | None) -> str:
    if not route:
        return "unknown"
    route = route.strip().lower()
    return route or "unknown"


def _norm_method(method: str | None) -> str:
    if not method:
        return "unknown"
    method = method.strip().upper()
    return method or "unknown"


def _norm_status_code(status_code: int | str | None) -> str:
    if status_code is None:
        return "unknown"
    if isinstance(status_code, int):
        return str(status_code)
    status_code = status_code.strip()
    return status_code or "unknown"


def _norm_outcome(outcome: str | None) -> str:
    if not outcome:
        return "unknown"
    outcome = outcome.strip().lower().replace(" ", "_")
    return outcome or "unknown"


def _norm_model(model: str | None) -> str:
    if not model:
        return "unknown"
    model = model.strip().lower()
    return model or "unknown"


def _status_class_from_code(code: int | None) -> str:
    if code is None:
        return "unknown"
    if 100 <= code <= 599:
        return f"{code // 100}xx"
    return "unknown"


def _normalize_error_type(error_type: str | None) -> str:
    if not error_type:
        return "unknown_error"
    normalized = error_type.strip().lower().replace(" ", "_")
    return normalized or "unknown_error"


@contextmanager
def track_in_progress(route: str, method: str) -> Iterator[None]:
    route_l = _norm_route(route)
    method_l = _norm_method(method)
    API_IN_PROGRESS.labels(route=route_l, method=method_l).inc()
    try:
        yield
    finally:
        API_IN_PROGRESS.labels(route=route_l, method=method_l).dec()


def record_api_request(
    *,
    route: str,
    method: str,
    status_code: int | str,
    duration_seconds: float,
) -> None:
    route_l = _norm_route(route)
    method_l = _norm_method(method)
    status_l = _norm_status_code(status_code)

    API_REQUESTS_TOTAL.labels(route=route_l, method=method_l, status_code=status_l).inc()
    API_REQUEST_DURATION_SECONDS.labels(
        route=route_l,
        method=method_l,
        status_code=status_l,
    ).observe(max(duration_seconds, 0.0))


def record_parser_result(
    *,
    outcome: str,
    duration_seconds: float,
) -> None:
    outcome_l = _norm_outcome(outcome)
    PARSER_REQUESTS_TOTAL.labels(outcome=outcome_l).inc()
    PARSER_DURATION_SECONDS.labels(outcome=outcome_l).observe(max(duration_seconds, 0.0))


def record_fallback(reason: str) -> None:
    normalized = reason.strip().lower().replace(" ", "_") if reason else "unknown"
    FALLBACKS_TOTAL.labels(reason=normalized).inc()


def record_job_description_size(text: str) -> None:
    JOB_DESCRIPTION_SIZE_CHARS.observe(float(max(len(text), 0)))


def classify_vllm_error(exc: Exception) -> tuple[str, str]:
    if isinstance(exc, httpx.TimeoutException):
        return "timeout", "timeout"
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code if exc.response is not None else None
        return "http_status_error", _status_class_from_code(code)
    if isinstance(exc, httpx.RequestError):
        return "request_error", "network"
    return "unexpected_error", "unknown"


def record_vllm_result(
    *,
    model: str,
    outcome: str,
    duration_seconds: float,
) -> None:
    model_l = _norm_model(model)
    outcome_l = _norm_outcome(outcome)
    VLLM_REQUESTS_TOTAL.labels(model=model_l, outcome=outcome_l).inc()
    VLLM_REQUEST_DURATION_SECONDS.labels(model=model_l, outcome=outcome_l).observe(
        max(duration_seconds, 0.0)
    )


def record_vllm_error(
    *,
    model: str,
    error_type: str,
    status_class: str,
) -> None:
    VLLM_ERRORS_TOTAL.labels(
        model=_norm_model(model),
        error_type=_normalize_error_type(error_type),
        status_class=_norm_outcome(status_class),
    ).inc()


@contextmanager
def observe_parser_duration(outcome: str = "unknown") -> Iterator[dict[str, str]]:
    state = {"outcome": outcome}
    started = perf_counter()
    try:
        yield state
    except Exception:
        state.setdefault("outcome", "error")
        raise
    finally:
        record_parser_result(
            outcome=state.get("outcome", "unknown"),
            duration_seconds=perf_counter() - started,
        )


@contextmanager
def observe_vllm_duration(
    model: str = "jobs_lora",
    outcome: str = "unknown",
) -> Iterator[dict[str, str]]:
    state = {"model": model, "outcome": outcome}
    started = perf_counter()
    try:
        yield state
    except Exception:
        state.setdefault("outcome", "error")
        raise
    finally:
        record_vllm_result(
            model=state.get("model", model),
            outcome=state.get("outcome", outcome),
            duration_seconds=perf_counter() - started,
        )


def setup_metrics(
    app: FastAPI,
    *,
    enabled: bool = True,
    metrics_path: str = "/metrics",
    should_group_status_codes: bool = False,
    should_ignore_untemplated: bool = True,
) -> Instrumentator | None:
    if not enabled:
        return None
    instrumentator = Instrumentator(
        should_group_status_codes=should_group_status_codes,
        should_ignore_untemplated=should_ignore_untemplated,
        should_respect_env_var=False,
        should_instrument_requests_inprogress=False,
    )
    instrumentator.instrument(app).expose(app, endpoint=metrics_path, include_in_schema=False)
    return instrumentator


__all__ = [
    "API_IN_PROGRESS",
    "API_REQUEST_DURATION_SECONDS",
    "API_REQUESTS_TOTAL",
    "FALLBACKS_TOTAL",
    "JOB_DESCRIPTION_SIZE_CHARS",
    "PARSER_DURATION_SECONDS",
    "PARSER_REQUESTS_TOTAL",
    "VLLM_ERRORS_TOTAL",
    "VLLM_REQUEST_DURATION_SECONDS",
    "VLLM_REQUESTS_TOTAL",
    "classify_vllm_error",
    "observe_parser_duration",
    "observe_vllm_duration",
    "record_api_request",
    "record_fallback",
    "record_job_description_size",
    "record_parser_result",
    "record_vllm_error",
    "record_vllm_result",
    "setup_metrics",
    "track_in_progress",
]