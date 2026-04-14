"""Unit tests for znotion.resources.search.SearchResource."""

from __future__ import annotations

import json
from typing import Any

import httpx

from znotion import (
    DatabaseObject,
    NotionClient,
    Page,
    PageObject,
    SearchResource,
)


def _page_payload(*, page_id: str = "p1") -> dict[str, Any]:
    return {
        "object": "page",
        "id": page_id,
        "created_time": "2024-01-01T00:00:00.000Z",
        "last_edited_time": "2024-01-02T00:00:00.000Z",
        "parent": {"type": "workspace", "workspace": True},
        "archived": False,
        "in_trash": False,
        "properties": {},
    }


def _database_payload(*, database_id: str = "db1") -> dict[str, Any]:
    return {
        "object": "database",
        "id": database_id,
        "created_time": "2024-01-01T00:00:00.000Z",
        "last_edited_time": "2024-01-02T00:00:00.000Z",
        "title": [],
        "description": [],
        "icon": None,
        "cover": None,
        "parent": {"type": "workspace", "workspace": True},
        "url": f"https://www.notion.so/{database_id}",
        "archived": False,
        "in_trash": False,
        "is_inline": False,
        "properties": {},
    }


def _make_client(handler: Any) -> NotionClient:
    return NotionClient(token="secret_test", transport=httpx.MockTransport(handler))


async def test_search_page_posts_payload_and_parses_mixed_results() -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["path"] = request.url.path
        seen["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "object": "list",
                "type": "page_or_database",
                "results": [
                    _page_payload(page_id="p1"),
                    _database_payload(database_id="db1"),
                ],
                "next_cursor": None,
                "has_more": False,
            },
        )

    async with _make_client(handler) as client:
        result = await client.search.search_page(
            query="hello",
            filter={"property": "object", "value": "page"},
            sort={"direction": "descending", "timestamp": "last_edited_time"},
            page_size=25,
        )

    assert seen["method"] == "POST"
    assert seen["path"] == "/v1/search"
    assert seen["body"] == {
        "query": "hello",
        "filter": {"property": "object", "value": "page"},
        "sort": {"direction": "descending", "timestamp": "last_edited_time"},
        "page_size": 25,
    }
    assert isinstance(result, Page)
    assert len(result.results) == 2
    assert isinstance(result.results[0], PageObject)
    assert result.results[0].id == "p1"
    assert isinstance(result.results[1], DatabaseObject)
    assert result.results[1].id == "db1"


async def test_search_page_omits_empty_body() -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(request.content)
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
        await client.search.search_page()

    assert seen["body"] == {}


async def test_search_page_forwards_start_cursor() -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(request.content)
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
        await client.search.search_page(start_cursor="cur-x")

    assert seen["body"] == {"start_cursor": "cur-x"}


async def test_search_page_filter_database_only() -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "object": "list",
                "results": [_database_payload(database_id="db2")],
                "next_cursor": None,
                "has_more": False,
            },
        )

    async with _make_client(handler) as client:
        result = await client.search.search_page(
            filter={"property": "object", "value": "database"},
        )

    assert seen["body"] == {"filter": {"property": "object", "value": "database"}}
    assert len(result.results) == 1
    assert isinstance(result.results[0], DatabaseObject)


async def test_search_auto_paginates_across_pages() -> None:
    call_bodies: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        call_bodies.append(body)
        if body.get("start_cursor") is None:
            return httpx.Response(
                200,
                json={
                    "object": "list",
                    "results": [
                        _page_payload(page_id="p1"),
                        _database_payload(database_id="db1"),
                    ],
                    "next_cursor": "cursor-2",
                    "has_more": True,
                },
            )
        return httpx.Response(
            200,
            json={
                "object": "list",
                "results": [_page_payload(page_id="p2")],
                "next_cursor": None,
                "has_more": False,
            },
        )

    async with _make_client(handler) as client:
        iterator = client.search.search(
            query="thing",
            sort={"direction": "ascending", "timestamp": "last_edited_time"},
            page_size=2,
        )
        items = [item async for item in iterator]

    assert [item.id for item in items] == ["p1", "db1", "p2"]
    assert isinstance(items[0], PageObject)
    assert isinstance(items[1], DatabaseObject)
    assert isinstance(items[2], PageObject)
    assert len(call_bodies) == 2
    assert call_bodies[0]["query"] == "thing"
    assert call_bodies[0]["page_size"] == 2
    assert call_bodies[0]["sort"] == {
        "direction": "ascending",
        "timestamp": "last_edited_time",
    }
    assert "start_cursor" not in call_bodies[0]
    assert call_bodies[1]["query"] == "thing"
    assert call_bodies[1]["start_cursor"] == "cursor-2"
    assert call_bodies[1]["page_size"] == 2


async def test_search_stops_on_missing_cursor() -> None:
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(
            200,
            json={
                "object": "list",
                "results": [_page_payload(page_id="p1")],
                "next_cursor": None,
                "has_more": True,
            },
        )

    async with _make_client(handler) as client:
        iterator = client.search.search()
        items = [item async for item in iterator]

    assert len(items) == 1
    assert len(calls) == 1


async def test_search_stops_on_has_more_false() -> None:
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(
            200,
            json={
                "object": "list",
                "results": [_page_payload(page_id="p1")],
                "next_cursor": "stale-cursor",
                "has_more": False,
            },
        )

    async with _make_client(handler) as client:
        iterator = client.search.search()
        items = [item async for item in iterator]

    assert len(items) == 1
    assert len(calls) == 1


async def test_client_exposes_search_accessor() -> None:
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
        assert isinstance(client.search, SearchResource)
        result = await client.search.search_page()
        assert isinstance(result, Page)
