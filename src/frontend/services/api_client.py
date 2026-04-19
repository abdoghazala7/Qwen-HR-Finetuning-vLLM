from __future__ import annotations

import os
from typing import Any

import requests

API_BASE_URL = os.getenv("API_BASE_URL", "http://fastapi:8000").rstrip("/")
PARSE_ENDPOINT = "/api/v1/job-descriptions/parse"
HEALTH_ENDPOINT = "/api/v1/"
SCHEMA_ENDPOINT = "/api/v1/job-descriptions/schema"
REQUEST_TIMEOUT_SECONDS = float(os.getenv("API_REQUEST_TIMEOUT_SECONDS", "90"))
HEALTH_TIMEOUT_SECONDS = 2.0
SCHEMA_TIMEOUT_SECONDS = 3.0


class ParserAPIClientError(Exception):
    pass


def _extract_error_message(response: requests.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text.strip() or "Unknown backend error."

    detail = payload.get("detail")
    if isinstance(detail, str):
        return detail
    if isinstance(detail, list):
        return ", ".join(
            item.get("msg", str(item)) if isinstance(item, dict) else str(item)
            for item in detail
        )
    if isinstance(detail, dict):
        return str(detail)

    return str(payload)


def check_api_health() -> bool:
    try:
        response = requests.get(
            f"{API_BASE_URL}{HEALTH_ENDPOINT}",
            timeout=HEALTH_TIMEOUT_SECONDS,
        )
        return response.status_code == 200
    except requests.RequestException:
        return False


def fetch_job_schema() -> dict[str, Any] | None:
    try:
        response = requests.get(
            f"{API_BASE_URL}{SCHEMA_ENDPOINT}",
            timeout=SCHEMA_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError):
        return None

    return payload if isinstance(payload, dict) else None


def parse_job_description(text: str) -> dict[str, Any]:
    url = f"{API_BASE_URL}{PARSE_ENDPOINT}"

    try:
        response = requests.post(
            url,
            json={"text": text},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        raise ParserAPIClientError(f"Unable to reach backend at {url}. {exc}") from exc

    if response.status_code != 200:
        message = _extract_error_message(response)
        raise ParserAPIClientError(
            f"Backend returned HTTP {response.status_code}: {message}"
        )

    try:
        return response.json()
    except ValueError as exc:
        raise ParserAPIClientError("Backend returned a non-JSON response.") from exc
