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
    assert seen["content-type"] is None
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
        assert inner is not None
        assert not inner.is_closed

    assert inner.is_closed
    assert client._transport._client is None


async def test_transport_one_shot_mode_without_async_with():
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.method)
        return _ok({"object": "page", "id": "abc"})

    t = Transport("tok", transport=httpx.MockTransport(handler))
    assert t._client is None

    result1 = await t.get("/pages/abc")
    result2 = await t.post("/pages", json={"parent": {"page_id": "root"}})

    assert result1 == {"object": "page", "id": "abc"}
    assert result2 == {"object": "page", "id": "abc"}
    assert seen == ["GET", "POST"]
    assert t._client is None


async def test_transport_one_shot_mode_patch_and_delete():
    seen: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append((request.method, request.url.path))
        return _ok()

    t = Transport("tok", transport=httpx.MockTransport(handler))
    await t.patch("/pages/p1", json={"archived": True})
    await t.delete("/blocks/b1")

    assert seen == [
        ("PATCH", "/v1/pages/p1"),
        ("DELETE", "/v1/blocks/b1"),
    ]
    assert t._client is None


async def test_transport_one_shot_mode_sends_headers():
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["authorization"] = request.headers.get("authorization")
        seen["notion-version"] = request.headers.get("notion-version")
        return _ok()

    t = Transport("secret_one_shot", transport=httpx.MockTransport(handler))
    await t.get("/pages/abc")

    assert seen["authorization"] == "Bearer secret_one_shot"
    assert seen["notion-version"] == DEFAULT_NOTION_VERSION


async def test_transport_one_shot_mode_raises_notion_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"code": "object_not_found", "message": "nope"})

    t = Transport("tok", transport=httpx.MockTransport(handler))
    with pytest.raises(NotionNotFoundError):
        await t.get("/pages/missing")
    assert t._client is None


async def test_transport_one_shot_mode_post_multipart():
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["content-type"] = request.headers.get("content-type")
        seen["body"] = bytes(request.content)
        return _ok({"id": "upload_1"})

    t = Transport("tok", transport=httpx.MockTransport(handler))
    result = await t.post_multipart(
        "/file_uploads/u1/send",
        files={"file": ("hello.txt", b"hi", "text/plain")},
        data={"part_number": "1"},
    )

    assert result == {"id": "upload_1"}
    assert seen["method"] == "POST"
    assert isinstance(seen["content-type"], str)
    assert seen["content-type"].startswith("multipart/form-data")
    assert b"hello.txt" in seen["body"]
    assert b"hi" in seen["body"]
    assert t._client is None


async def test_notion_client_without_async_with(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("NOTION_TOKEN", "secret_no_ctx")

    def handler(request: httpx.Request) -> httpx.Response:
        return _ok({"object": "page", "id": "p1"})

    client = NotionClient(transport=httpx.MockTransport(handler))
    assert client._transport._client is None

    result = await client._transport.get("/pages/p1")
    assert result == {"object": "page", "id": "p1"}
    assert client._transport._client is None


async def test_transport_close_is_noop_when_not_entered():
    t = Transport("tok", transport=httpx.MockTransport(lambda r: _ok()))
    assert t._client is None
    await t.close()
    assert t._client is None
