"""Unit tests for znotion.http.Transport."""

from __future__ import annotations

import json

import httpx
import pytest

from znotion import NotionClient
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
from znotion.http import (
    DEFAULT_BASE_URL,
    DEFAULT_NOTION_VERSION,
    Transport,
)


def _ok(body: dict[str, object] | None = None) -> httpx.Response:
    return httpx.Response(200, json=body if body is not None else {"ok": True})


async def test_sends_required_headers_on_get():
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["authorization"] = request.headers.get("authorization")
        seen["notion-version"] = request.headers.get("notion-version")
        seen["content-type"] = request.headers.get("content-type")
        seen["url"] = str(request.url)
        seen["method"] = request.method
        return _ok({"object": "page", "id": "abc"})

    async with Transport(
        "secret_test_token",
        transport=httpx.MockTransport(handler),
    ) as t:
        result = await t.get("/pages/abc")

    assert result == {"object": "page", "id": "abc"}
    assert seen["authorization"] == "Bearer secret_test_token"
    assert seen["notion-version"] == DEFAULT_NOTION_VERSION
    assert seen["content-type"] == "application/json"
    assert seen["url"] == f"{DEFAULT_BASE_URL}/pages/abc"
    assert seen["method"] == "GET"


async def test_custom_base_url_and_notion_version():
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["notion-version"] = request.headers.get("notion-version")
        seen["url"] = str(request.url)
        return _ok()

    async with Transport(
        "tok",
        base_url="https://example.test/api",
        notion_version="2099-01-01",
        transport=httpx.MockTransport(handler),
    ) as t:
        await t.get("/ping")

    assert seen["notion-version"] == "2099-01-01"
    assert seen["url"] == "https://example.test/api/ping"


async def test_post_serializes_json_body():
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["body"] = request.content
        return _ok({"object": "page"})

    payload = {"parent": {"page_id": "root"}, "properties": {}}
    async with Transport("tok", transport=httpx.MockTransport(handler)) as t:
        result = await t.post("/pages", json=payload)

    assert result == {"object": "page"}
    assert seen["method"] == "POST"
    assert isinstance(seen["body"], (bytes, bytearray))
    assert json.loads(bytes(seen["body"])) == payload


async def test_patch_and_delete_methods():
    seen: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append((request.method, request.url.path))
        return _ok()

    async with Transport("tok", transport=httpx.MockTransport(handler)) as t:
        await t.patch("/pages/p1", json={"archived": True})
        await t.delete("/blocks/b1")

    assert seen == [
        ("PATCH", "/v1/pages/p1"),
        ("DELETE", "/v1/blocks/b1"),
    ]


async def test_get_forwards_query_params():
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["query"] = dict(request.url.params)
        return _ok({"results": []})

    async with Transport("tok", transport=httpx.MockTransport(handler)) as t:
        await t.get("/blocks/x/children", params={"page_size": 2, "start_cursor": "c"})

    assert seen["query"] == {"page_size": "2", "start_cursor": "c"}


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
        (503, NotionServerError),
    ],
)
async def test_non_2xx_maps_to_notion_error(
    status: int, expected: type[NotionError]
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status,
            json={"code": "bad_thing", "message": "nope", "request_id": "req-42"},
        )

    async with Transport("tok", transport=httpx.MockTransport(handler)) as t:
        with pytest.raises(expected) as exc_info:
            await t.get("/pages/abc")

    err = exc_info.value
    assert isinstance(err, NotionError)
    assert err.status == status
    assert err.code == "bad_thing"
    assert err.message == "nope"
    assert err.request_id == "req-42"


async def test_non_dict_json_body_raises_notion_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[1, 2, 3])

    async with Transport("tok", transport=httpx.MockTransport(handler)) as t:
        with pytest.raises(NotionError):
            await t.get("/pages/abc")


async def test_notion_client_async_context_closes_transport(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("NOTION_TOKEN", "secret_ctx")

    def handler(request: httpx.Request) -> httpx.Response:
        return _ok()

    mock = httpx.MockTransport(handler)
    async with NotionClient(transport=mock) as client:
        assert client._token == "secret_ctx"
        inner = client._transport._client
        assert not inner.is_closed

    assert inner.is_closed
