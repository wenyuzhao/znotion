"""Unit tests for znotion.resources.data_sources.DataSourcesResource."""

from __future__ import annotations

import json
from typing import Any

import httpx

from znotion import DataSourceObject, NotionClient, Page, PageObject
from znotion.models.parent import DataSourceParent


def _data_source_payload(
    *,
    data_source_id: str = "ds-123",
    database_id: str = "db-1",
) -> dict[str, Any]:
    return {
        "object": "data_source",
        "id": data_source_id,
        "created_time": "2024-01-01T00:00:00.000Z",
        "last_edited_time": "2024-01-02T00:00:00.000Z",
        "title": [{"type": "text", "text": {"content": "Tasks"}, "plain_text": "Tasks"}],
        "description": [],
        "icon": None,
        "cover": None,
        "parent": {"type": "database_id", "database_id": database_id},
        "url": f"https://www.notion.so/{data_source_id}",
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


def _page_payload(*, page_id: str, data_source_id: str = "ds-123") -> dict[str, Any]:
    return {
        "object": "page",
        "id": page_id,
        "created_time": "2024-01-01T00:00:00.000Z",
        "last_edited_time": "2024-01-02T00:00:00.000Z",
        "parent": {"type": "data_source_id", "data_source_id": data_source_id},
        "is_archived": False,
        "in_trash": False,
        "properties": {},
    }


def _make_client(handler: Any) -> NotionClient:
    return NotionClient(token="secret_test", transport=httpx.MockTransport(handler))


async def test_create_posts_parent_and_properties() -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["path"] = request.url.path
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json=_data_source_payload())

    async with _make_client(handler) as client:
        ds = await client.data_sources.create(
            parent={"database_id": "db-1"},
            properties={"Name": {"title": {}}},
            title=[{"type": "text", "text": {"content": "Tasks"}}],
        )

    assert seen["method"] == "POST"
    assert seen["path"] == "/v1/data_sources"
    assert seen["body"]["parent"] == {"database_id": "db-1"}
    assert seen["body"]["properties"] == {"Name": {"title": {}}}
    assert seen["body"]["title"] == [{"type": "text", "text": {"content": "Tasks"}}]
    assert isinstance(ds, DataSourceObject)
    assert ds.id == "ds-123"
    assert "Name" in ds.properties


async def test_retrieve_returns_data_source_object() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/v1/data_sources/ds-123"
        return httpx.Response(200, json=_data_source_payload())

    async with _make_client(handler) as client:
        ds = await client.data_sources.retrieve("ds-123")

    assert isinstance(ds, DataSourceObject)
    assert ds.id == "ds-123"
    assert "Tags" in ds.properties
    assert ds.properties["Tags"].type == "multi_select"


async def test_update_patches_properties_and_title() -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["path"] = request.url.path
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json=_data_source_payload())

    async with _make_client(handler) as client:
        await client.data_sources.update(
            "ds-123",
            title=[{"type": "text", "text": {"content": "Renamed"}}],
            properties={"Extra": {"rich_text": {}}},
            in_trash=False,
        )

    assert seen["method"] == "PATCH"
    assert seen["path"] == "/v1/data_sources/ds-123"
    assert seen["body"] == {
        "title": [{"type": "text", "text": {"content": "Renamed"}}],
        "properties": {"Extra": {"rich_text": {}}},
        "in_trash": False,
    }


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
                "type": "page_or_data_source",
                "results": [
                    _page_payload(page_id="p1"),
                    _page_payload(page_id="p2"),
                ],
                "next_cursor": None,
                "has_more": False,
            },
        )

    async with _make_client(handler) as client:
        result = await client.data_sources.query_page(
            "ds-123",
            filter={"property": "Name", "title": {"is_not_empty": True}},
            sorts=[{"property": "Name", "direction": "ascending"}],
            page_size=50,
        )

    assert seen["method"] == "POST"
    assert seen["path"] == "/v1/data_sources/ds-123/query"
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
        await client.data_sources.query_page("ds-123")

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
        await client.data_sources.query_page("ds-123", start_cursor="cur-x")

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
        iterator = client.data_sources.query(
            "ds-123",
            filter={"property": "Name", "title": {"is_not_empty": True}},
            page_size=2,
        )
        items = [item async for item in iterator]

    assert [item.id for item in items] == ["p1", "p2", "p3"]
    assert len(call_bodies) == 2
    assert call_bodies[0]["page_size"] == 2
    assert "start_cursor" not in call_bodies[0]
    assert call_bodies[1]["start_cursor"] == "cursor-2"
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
        iterator = client.data_sources.query("ds-123")
        items = [item async for item in iterator]

    assert len(items) == 1
    assert len(calls) == 1


async def test_data_source_parent_model_round_trips() -> None:
    parent = DataSourceParent(data_source_id="ds-xyz")
    assert parent.type == "data_source_id"
    dumped = parent.model_dump()
    assert dumped == {"type": "data_source_id", "data_source_id": "ds-xyz"}


async def test_client_exposes_data_sources_accessor() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_data_source_payload())

    async with _make_client(handler) as client:
        assert client.data_sources is not None
        ds = await client.data_sources.retrieve("ds-123")
        assert ds.id == "ds-123"
