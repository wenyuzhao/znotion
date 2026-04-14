"""Tests for znotion.errors.NotionError.from_response and subclass mapping."""

from __future__ import annotations

import httpx
import pytest

from znotion.errors import (
    NotionAuthError,
    NotionConflictError,
    NotionError,
    NotionForbiddenError,
    NotionNotFoundError,
    NotionRateLimitError,
    NotionServerError,
    NotionValidationError,
)


def _response(
    status: int,
    *,
    code: str | None = "some_code",
    message: str | None = "something went wrong",
    request_id: str | None = "req_abc123",
) -> httpx.Response:
    body: dict[str, str] = {}
    if code is not None:
        body["code"] = code
    if message is not None:
        body["message"] = message
    if request_id is not None:
        body["request_id"] = request_id
    return httpx.Response(status_code=status, json=body)


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (400, NotionValidationError),
        (401, NotionAuthError),
        (403, NotionForbiddenError),
        (404, NotionNotFoundError),
        (409, NotionConflictError),
        (429, NotionRateLimitError),
        (500, NotionServerError),
        (502, NotionServerError),
        (503, NotionServerError),
    ],
)
def test_status_maps_to_subclass(status: int, expected: type[NotionError]) -> None:
    err = NotionError.from_response(_response(status))

    assert isinstance(err, expected)
    assert isinstance(err, NotionError)
    assert err.status == status
    assert err.code == "some_code"
    assert err.message == "something went wrong"
    assert err.request_id == "req_abc123"
    assert str(err) == "something went wrong"


def test_unknown_status_falls_back_to_base() -> None:
    err = NotionError.from_response(_response(418))

    assert type(err) is NotionError
    assert err.status == 418


def test_missing_body_uses_status_fallback_message() -> None:
    response = httpx.Response(status_code=500, content=b"")

    err = NotionError.from_response(response)

    assert isinstance(err, NotionServerError)
    assert err.status == 500
    assert err.code is None
    assert err.request_id is None
    assert err.message == "HTTP 500"


def test_non_json_body_uses_text_as_message() -> None:
    response = httpx.Response(
        status_code=503,
        content=b"upstream is down",
        headers={"content-type": "text/plain"},
    )

    err = NotionError.from_response(response)

    assert isinstance(err, NotionServerError)
    assert err.message == "upstream is down"
    assert err.code is None


def test_partial_json_body_keeps_known_fields() -> None:
    response = httpx.Response(
        status_code=404,
        json={"code": "object_not_found", "message": "Block not found"},
    )

    err = NotionError.from_response(response)

    assert isinstance(err, NotionNotFoundError)
    assert err.code == "object_not_found"
    assert err.message == "Block not found"
    assert err.request_id is None


def test_base_constructor_stores_attributes() -> None:
    err = NotionError("boom", status=418, code="teapot", request_id="req_1")

    assert err.message == "boom"
    assert err.status == 418
    assert err.code == "teapot"
    assert err.request_id == "req_1"
    assert str(err) == "boom"
