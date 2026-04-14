"""Unit tests for znotion.resources.databases.DatabasesResource."""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from znotion import DatabaseObject, NotionClient, Page, PageObject
from znotion.models.parent import PageParent


def _database_payload(
    *,
    database_id: str = "db-123",
    parent_id: str = "parent-1",
    title_text: str = "My DB",
) -> dict[str, Any]:
    return {
        "object": "database",
        "id": database_id,
        "created_time": "2024-01-01T00:00:00.000Z",
        "last_edited_time": "2024-01-02T00:00:00.000Z",
        "created_by": {"object": "user", "id": "u1"},
        "last_edited_by": {"object": "user", "id": "u2"},
        "title": [
            {
                "type": "text",
                "text": {"content": title_text},
                "plain_text": title_text,
            }
        ],
        "description": [],
        "icon": {"type": "emoji", "emoji": "📚"},
        "cover": None,
        "parent": {"type": "page_id", "page_id": parent_id},
        "url": f"https://www.notion.so/{database_id}",
        "archived": False,
        "in_trash": False,
        "is_inline": False,
        "properties": {
            "Name": {
                "id": "title",
                "name": "Name",
                "type": "title",
                "title": {},
            },
            "Tags": {
                "id": "prop-tags",
                "name": "Tags",
                "type": "multi_select",
                "multi_select": {"options": []},
            },
        },
    }


def _page_payload(*, page_id: str) -> dict[str, Any]:
    return {
        "object": "page",
        "id": page_id,
        "created_time": "2024-01-01T00:00:00.000Z",
        "last_edited_time": "2024-01-02T00:00:00.000Z",
        "parent": {"type": "database_id", "database_id": "db-123"},
        "archived": False,
        "in_trash": False,
        "properties": {},
    }


def _make_client(handler: Any) -> NotionClient:
    return NotionClient(token="secret_test", transport=httpx.MockTransport(handler))


async def test_create_posts_payload_and_returns_database() -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["path"] = request.url.path
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json=_database_payload())

    async with _make_client(handler) as client:
        db = await client.databases.create(
            parent=PageParent(page_id="parent-1"),
            title=[{"type": "text", "text": {"content": "My DB"}}],
            properties={
                "Name": {"title": {}},
                "Tags": {"multi_select": {"options": []}},
            },
            icon={"type": "emoji", "emoji": "📚"},
        )

    assert seen["method"] == "POST"
    assert seen["path"] == "/v1/databases"
    assert seen["body"]["parent"] == {"type": "page_id", "page_id": "parent-1"}
    assert seen["body"]["title"] == [{"type": "text", "text": {"content": "My DB"}}]
    assert "properties" in seen["body"]
    assert seen["body"]["icon"] == {"type": "emoji", "emoji": "📚"}
    assert "cover" not in seen["body"]
    assert "description" not in seen["body"]
    assert "is_inline" not in seen["body"]
    assert isinstance(db, DatabaseObject)
    assert db.id == "db-123"
    assert "Name" in db.properties


@pytest.mark.parametrize(
    "missing",
    ["title", "description", "properties", "icon", "cover", "is_inline"],
)
async def test_create_omits_unspecified_fields(missing: str) -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json=_database_payload())

    async with _make_client(handler) as client:
        await client.databases.create(parent={"type": "page_id", "page_id": "p1"})

    assert missing not in seen["body"]
    assert seen["body"] == {"parent": {"type": "page_id", "page_id": "p1"}}


async def test_retrieve_returns_database_object() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/v1/databases/db-123"
        return httpx.Response(200, json=_database_payload())

    async with _make_client(handler) as client:
        db = await client.databases.retrieve("db-123")

    assert isinstance(db, DatabaseObject)
    assert db.id == "db-123"
    assert db.parent.type == "page_id"
    assert len(db.title) == 1
    assert "Tags" in db.properties


async def test_update_patches_only_provided_fields() -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["path"] = request.url.path
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json=_database_payload())

    async with _make_client(handler) as client:
        await client.databases.update(
            "db-123",
            title=[{"type": "text", "text": {"content": "New"}}],
            archived=True,
        )

    assert seen["method"] == "PATCH"
    assert seen["path"] == "/v1/databases/db-123"
    assert seen["body"] == {
        "title": [{"type": "text", "text": {"content": "New"}}],
        "archived": True,
    }


async def test_update_supports_description_properties_and_icon() -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json=_database_payload())

    async with _make_client(handler) as client:
        await client.databases.update(
            "db-123",
            description=[{"type": "text", "text": {"content": "desc"}}],
            properties={"Status": {"select": {"options": []}}},
            icon={"type": "emoji", "emoji": "🔥"},
            cover={"type": "external", "external": {"url": "https://x.test/c.png"}},
        )

    assert seen["body"]["description"] == [
        {"type": "text", "text": {"content": "desc"}}
    ]
    assert seen["body"]["properties"] == {"Status": {"select": {"options": []}}}
    assert seen["body"]["icon"] == {"type": "emoji", "emoji": "🔥"}
    assert seen["body"]["cover"] == {
        "type": "external",
        "external": {"url": "https://x.test/c.png"},
    }
    assert "title" not in seen["body"]
    assert "archived" not in seen["body"]


async def test_query_page_posts_body_and_returns_page() -> None:
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
                "results": [_page_payload(page_id="p1"), _page_payload(page_id="p2")],
                "next_cursor": None,
                "has_more": False,
            },
        )

    async with _make_client(handler) as client:
        result = await client.databases.query_page(
            "db-123",
            filter={"property": "Name", "title": {"is_not_empty": True}},
            sorts=[{"property": "Name", "direction": "ascending"}],
            page_size=50,
        )

    assert seen["method"] == "POST"
    assert seen["path"] == "/v1/databases/db-123/query"
    assert seen["body"]["filter"] == {
        "property": "Name",
        "title": {"is_not_empty": True},
    }
    assert seen["body"]["sorts"] == [{"property": "Name", "direction": "ascending"}]
    assert seen["body"]["page_size"] == 50
    assert "start_cursor" not in seen["body"]
    assert isinstance(result, Page)
    assert len(result.results) == 2
    assert isinstance(result.results[0], PageObject)
    assert result.results[0].id == "p1"


async def test_query_page_omits_empty_body_fields() -> None:
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
        await client.databases.query_page("db-123")

    assert seen["body"] == {}


async def test_query_page_forwards_start_cursor() -> None:
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
        await client.databases.query_page("db-123", start_cursor="cur-x")

    assert seen["body"] == {"start_cursor": "cur-x"}


async def test_query_auto_paginates_across_pages() -> None:
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
                        _page_payload(page_id="p2"),
                    ],
                    "next_cursor": "cursor-2",
                    "has_more": True,
                },
            )
        return httpx.Response(
            200,
            json={
                "object": "list",
                "results": [_page_payload(page_id="p3")],
                "next_cursor": None,
                "has_more": False,
            },
        )

    async with _make_client(handler) as client:
        iterator = client.databases.query(
            "db-123",
            filter={"property": "Name", "title": {"is_not_empty": True}},
            page_size=2,
        )
        items = [item async for item in iterator]

    assert [item.id for item in items] == ["p1", "p2", "p3"]
    assert len(call_bodies) == 2
    assert call_bodies[0]["page_size"] == 2
    assert call_bodies[0]["filter"] == {
        "property": "Name",
        "title": {"is_not_empty": True},
    }
    assert "start_cursor" not in call_bodies[0]
    assert call_bodies[1]["start_cursor"] == "cursor-2"
    assert call_bodies[1]["filter"] == {
        "property": "Name",
        "title": {"is_not_empty": True},
    }
    assert call_bodies[1]["page_size"] == 2


async def test_query_stops_on_missing_cursor() -> None:
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
        iterator = client.databases.query("db-123")
        items = [item async for item in iterator]

    assert len(items) == 1
    assert len(calls) == 1


async def test_client_exposes_databases_accessor() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_database_payload())

    async with _make_client(handler) as client:
        assert client.databases is not None
        db = await client.databases.retrieve("db-123")
        assert db.id == "db-123"
