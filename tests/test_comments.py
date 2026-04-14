"""Unit tests for znotion.resources.comments.CommentsResource."""

from __future__ import annotations

import json
from typing import Any

import httpx

from znotion import Comment, CommentsResource, NotionClient, Page


def _rich_text_dict(content: str) -> dict[str, Any]:
    return {
        "type": "text",
        "text": {"content": content, "link": None},
        "plain_text": content,
        "href": None,
        "annotations": {
            "bold": False,
            "italic": False,
            "strikethrough": False,
            "underline": False,
            "code": False,
            "color": "default",
        },
    }


def _comment_payload(
    *,
    comment_id: str = "c1",
    discussion_id: str = "d1",
    parent: dict[str, Any] | None = None,
    text: str = "hello world",
) -> dict[str, Any]:
    return {
        "object": "comment",
        "id": comment_id,
        "parent": parent or {"type": "page_id", "page_id": "page-1"},
        "discussion_id": discussion_id,
        "created_time": "2024-01-01T00:00:00.000Z",
        "last_edited_time": "2024-01-02T00:00:00.000Z",
        "created_by": {"object": "user", "id": "u1"},
        "rich_text": [_rich_text_dict(text)],
    }


def _make_client(handler: Any) -> NotionClient:
    return NotionClient(token="secret_test", transport=httpx.MockTransport(handler))


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------


async def test_create_page_comment_posts_parent_and_rich_text() -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["path"] = request.url.path
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json=_comment_payload())

    async with _make_client(handler) as client:
        result = await client.comments.create(
            parent={"page_id": "page-1"},
            rich_text=[_rich_text_dict("hello world")],
        )

    assert seen["method"] == "POST"
    assert seen["path"] == "/v1/comments"
    assert seen["body"] == {
        "parent": {"page_id": "page-1"},
        "rich_text": [_rich_text_dict("hello world")],
    }
    assert isinstance(result, Comment)
    assert result.id == "c1"
    assert result.discussion_id == "d1"
    assert len(result.rich_text) == 1


async def test_create_thread_reply_posts_discussion_id() -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json=_comment_payload(comment_id="c2", discussion_id="d-xyz"),
        )

    async with _make_client(handler) as client:
        result = await client.comments.create(
            discussion_id="d-xyz",
            rich_text=[_rich_text_dict("a reply")],
        )

    assert seen["body"] == {
        "discussion_id": "d-xyz",
        "rich_text": [_rich_text_dict("a reply")],
    }
    assert result.discussion_id == "d-xyz"


async def test_create_omits_parent_when_not_provided() -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json=_comment_payload())

    async with _make_client(handler) as client:
        await client.comments.create(
            discussion_id="d1",
            rich_text=[_rich_text_dict("x")],
        )

    assert "parent" not in seen["body"]


async def test_create_omits_discussion_id_when_not_provided() -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json=_comment_payload())

    async with _make_client(handler) as client:
        await client.comments.create(
            parent={"page_id": "page-1"},
            rich_text=[_rich_text_dict("x")],
        )

    assert "discussion_id" not in seen["body"]


# ---------------------------------------------------------------------------
# list_page
# ---------------------------------------------------------------------------


async def test_list_page_forwards_block_id_and_parses_results() -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["path"] = request.url.path
        seen["params"] = dict(request.url.params)
        return httpx.Response(
            200,
            json={
                "object": "list",
                "type": "comment",
                "results": [
                    _comment_payload(comment_id="c1"),
                    _comment_payload(comment_id="c2"),
                ],
                "next_cursor": None,
                "has_more": False,
            },
        )

    async with _make_client(handler) as client:
        result = await client.comments.list_page(block_id="block-1")

    assert seen["method"] == "GET"
    assert seen["path"] == "/v1/comments"
    assert seen["params"] == {"block_id": "block-1"}
    assert isinstance(result, Page)
    assert [c.id for c in result.results] == ["c1", "c2"]
    assert isinstance(result.results[0], Comment)


async def test_list_page_forwards_start_cursor_and_page_size() -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["params"] = dict(request.url.params)
        return httpx.Response(
            200,
            json={
                "object": "list",
                "results": [],
                "next_cursor": None,
                "has_more": False,
            },
        )

    async with _make_client(handler) as client:
        await client.comments.list_page(
            block_id="block-1",
            start_cursor="cur-x",
            page_size=25,
        )

    assert seen["params"] == {
        "block_id": "block-1",
        "start_cursor": "cur-x",
        "page_size": "25",
    }


async def test_list_page_omits_optional_params() -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["params"] = dict(request.url.params)
        return httpx.Response(
            200,
            json={
                "object": "list",
                "results": [],
                "next_cursor": None,
                "has_more": False,
            },
        )

    async with _make_client(handler) as client:
        await client.comments.list_page(block_id="block-1")

    assert seen["params"] == {"block_id": "block-1"}


# ---------------------------------------------------------------------------
# list (auto-pagination)
# ---------------------------------------------------------------------------


async def test_list_auto_paginates_across_pages() -> None:
    calls: list[dict[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        params = dict(request.url.params)
        calls.append(params)
        if "start_cursor" not in params:
            return httpx.Response(
                200,
                json={
                    "object": "list",
                    "results": [
                        _comment_payload(comment_id="c1"),
                        _comment_payload(comment_id="c2"),
                    ],
                    "next_cursor": "cursor-2",
                    "has_more": True,
                },
            )
        return httpx.Response(
            200,
            json={
                "object": "list",
                "results": [_comment_payload(comment_id="c3")],
                "next_cursor": None,
                "has_more": False,
            },
        )

    async with _make_client(handler) as client:
        iterator = client.comments.list(block_id="block-1", page_size=2)
        items = [item async for item in iterator]

    assert [c.id for c in items] == ["c1", "c2", "c3"]
    assert len(calls) == 2
    assert calls[0] == {"block_id": "block-1", "page_size": "2"}
    assert calls[1] == {
        "block_id": "block-1",
        "start_cursor": "cursor-2",
        "page_size": "2",
    }


async def test_list_stops_on_missing_cursor() -> None:
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(
            200,
            json={
                "object": "list",
                "results": [_comment_payload(comment_id="c1")],
                "next_cursor": None,
                "has_more": True,
            },
        )

    async with _make_client(handler) as client:
        iterator = client.comments.list(block_id="block-1")
        items = [item async for item in iterator]

    assert len(items) == 1
    assert len(calls) == 1


async def test_list_stops_on_has_more_false() -> None:
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(
            200,
            json={
                "object": "list",
                "results": [_comment_payload(comment_id="c1")],
                "next_cursor": "stale-cursor",
                "has_more": False,
            },
        )

    async with _make_client(handler) as client:
        iterator = client.comments.list(block_id="block-1")
        items = [item async for item in iterator]

    assert len(items) == 1
    assert len(calls) == 1


# ---------------------------------------------------------------------------
# Client accessor
# ---------------------------------------------------------------------------


async def test_client_exposes_comments_accessor() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "object": "list",
                "results": [],
                "next_cursor": None,
                "has_more": False,
            },
        )

    async with _make_client(handler) as client:
        assert isinstance(client.comments, CommentsResource)
        result = await client.comments.list_page(block_id="block-1")
        assert isinstance(result, Page)
