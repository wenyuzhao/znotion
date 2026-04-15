"""Unit tests for znotion.resources.databases.DatabasesResource."""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from znotion import DatabaseObject, NotionClient
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
        "in_trash": False,
        "is_inline": False,
        "is_locked": False,
        "data_sources": [
            {"id": "ds-1", "name": "Default"},
        ],
    }


def _make_client(handler: Any) -> NotionClient:
    return NotionClient(token="secret_test", transport=httpx.MockTransport(handler))


async def test_create_wraps_properties_under_initial_data_source() -> None:
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
    assert seen["body"]["initial_data_source"] == {
        "properties": {
            "Name": {"title": {}},
            "Tags": {"multi_select": {"options": []}},
        },
    }
    assert "properties" not in seen["body"]
    assert seen["body"]["icon"] == {"type": "emoji", "emoji": "📚"}
    assert "cover" not in seen["body"]
    assert "description" not in seen["body"]
    assert "is_inline" not in seen["body"]
    assert isinstance(db, DatabaseObject)
    assert db.id == "db-123"
    assert db.data_sources[0].id == "ds-1"


@pytest.mark.parametrize(
    "missing",
    ["title", "description", "initial_data_source", "icon", "cover", "is_inline"],
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
    assert db.parent is not None
    assert db.parent.type == "page_id"
    assert len(db.title) == 1
    assert db.data_sources[0].id == "ds-1"


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
            in_trash=True,
        )

    assert seen["method"] == "PATCH"
    assert seen["path"] == "/v1/databases/db-123"
    assert seen["body"] == {
        "title": [{"type": "text", "text": {"content": "New"}}],
        "in_trash": True,
    }


async def test_update_supports_description_icon_cover() -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json=_database_payload())

    async with _make_client(handler) as client:
        await client.databases.update(
            "db-123",
            description=[{"type": "text", "text": {"content": "desc"}}],
            icon={"type": "emoji", "emoji": "🔥"},
            cover={"type": "external", "external": {"url": "https://x.test/c.png"}},
        )

    assert seen["body"]["description"] == [
        {"type": "text", "text": {"content": "desc"}}
    ]
    assert seen["body"]["icon"] == {"type": "emoji", "emoji": "🔥"}
    assert seen["body"]["cover"] == {
        "type": "external",
        "external": {"url": "https://x.test/c.png"},
    }
    assert "title" not in seen["body"]
    assert "in_trash" not in seen["body"]
    assert "properties" not in seen["body"]


async def test_client_exposes_databases_accessor() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_database_payload())

    async with _make_client(handler) as client:
        assert client.databases is not None
        db = await client.databases.retrieve("db-123")
        assert db.id == "db-123"
