"""Unit tests for znotion.resources.pages.PagesResource."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx
import pytest

from znotion import NotionClient, Page, PageObject, PropertyItem
from znotion.models.parent import PageParent


def _page_payload(
    *,
    page_id: str = "page-123",
    parent_id: str = "parent-1",
    title_text: str = "hello",
    archived: bool = False,
) -> dict[str, Any]:
    return {
        "object": "page",
        "id": page_id,
        "created_time": "2024-01-01T00:00:00.000Z",
        "last_edited_time": "2024-01-02T00:00:00.000Z",
        "created_by": {"object": "user", "id": "u1"},
        "last_edited_by": {"object": "user", "id": "u2"},
        "parent": {"type": "page_id", "page_id": parent_id},
        "archived": archived,
        "in_trash": False,
        "url": f"https://www.notion.so/{page_id}",
        "properties": {
            "Name": {
                "id": "title",
                "type": "title",
                "title": [
                    {
                        "type": "text",
                        "text": {"content": title_text},
                        "plain_text": title_text,
                    }
                ],
            }
        },
    }


def _make_client(handler: Any) -> NotionClient:
    return NotionClient(token="secret_test", transport=httpx.MockTransport(handler))


async def test_create_posts_payload_and_returns_page() -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["path"] = request.url.path
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json=_page_payload())

    async with _make_client(handler) as client:
        page = await client.pages.create(
            parent=PageParent(page_id="parent-1"),
            properties={
                "Name": {
                    "title": [{"type": "text", "text": {"content": "hello"}}],
                }
            },
            children=[
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {"rich_text": []},
                }
            ],
            icon={"type": "emoji", "emoji": "📄"},
        )

    assert seen["method"] == "POST"
    assert seen["path"] == "/v1/pages"
    assert seen["body"]["parent"] == {"type": "page_id", "page_id": "parent-1"}
    assert "properties" in seen["body"]
    assert seen["body"]["children"][0]["type"] == "paragraph"
    assert seen["body"]["icon"] == {"type": "emoji", "emoji": "📄"}
    assert "cover" not in seen["body"]
    assert isinstance(page, PageObject)
    assert page.id == "page-123"
    assert page.parent.type == "page_id"


async def test_retrieve_returns_page_object() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/v1/pages/page-123"
        return httpx.Response(200, json=_page_payload())

    async with _make_client(handler) as client:
        page = await client.pages.retrieve("page-123")

    assert isinstance(page, PageObject)
    assert page.id == "page-123"
    assert page.created_by is not None
    assert page.created_by.id == "u1"
    assert "Name" in page.properties


async def test_update_patches_only_provided_fields() -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["path"] = request.url.path
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json=_page_payload(archived=True))

    async with _make_client(handler) as client:
        page = await client.pages.update(
            "page-123",
            archived=True,
            icon={"type": "emoji", "emoji": "🔥"},
        )

    assert seen["method"] == "PATCH"
    assert seen["path"] == "/v1/pages/page-123"
    assert seen["body"] == {
        "archived": True,
        "icon": {"type": "emoji", "emoji": "🔥"},
    }
    assert page.archived is True


async def test_update_supports_in_trash_and_properties() -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json=_page_payload())

    async with _make_client(handler) as client:
        await client.pages.update(
            "page-123",
            in_trash=True,
            properties={"Name": {"title": []}},
            cover={"type": "external", "external": {"url": "https://x.test/c.png"}},
        )

    assert seen["body"]["in_trash"] is True
    assert seen["body"]["properties"] == {"Name": {"title": []}}
    assert seen["body"]["cover"] == {
        "type": "external",
        "external": {"url": "https://x.test/c.png"},
    }


async def test_retrieve_property_returns_property_item_for_scalar() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/pages/page-123/properties/prop-num"
        return httpx.Response(
            200,
            json={
                "object": "property_item",
                "id": "prop-num",
                "type": "number",
                "number": 42,
            },
        )

    async with _make_client(handler) as client:
        result = await client.pages.retrieve_property("page-123", "prop-num")

    assert isinstance(result, PropertyItem)
    assert result.id == "prop-num"
    assert result.type == "number"
    dumped = result.model_dump(exclude_unset=True)
    assert dumped["number"] == 42


async def test_retrieve_property_page_returns_page_for_list() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "object": "list",
                "type": "property_item",
                "results": [
                    {
                        "object": "property_item",
                        "id": "title",
                        "type": "title",
                        "title": {"type": "text", "text": {"content": "a"}},
                    }
                ],
                "next_cursor": None,
                "has_more": False,
                "property_item": {"id": "title", "next_url": None},
            },
        )

    async with _make_client(handler) as client:
        result = await client.pages.retrieve_property_page("page-123", "title")

    assert isinstance(result, Page)
    assert len(result.results) == 1
    assert result.results[0].id == "title"


async def test_retrieve_property_auto_paginates_list_property() -> None:
    calls: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(dict(request.url.params))
        if request.url.params.get("start_cursor") is None:
            return httpx.Response(
                200,
                json={
                    "object": "list",
                    "type": "property_item",
                    "results": [
                        {
                            "object": "property_item",
                            "id": "title",
                            "type": "title",
                            "title": {"text": {"content": "a"}},
                        },
                        {
                            "object": "property_item",
                            "id": "title",
                            "type": "title",
                            "title": {"text": {"content": "b"}},
                        },
                    ],
                    "next_cursor": "cursor-2",
                    "has_more": True,
                },
            )
        return httpx.Response(
            200,
            json={
                "object": "list",
                "type": "property_item",
                "results": [
                    {
                        "object": "property_item",
                        "id": "title",
                        "type": "title",
                        "title": {"text": {"content": "c"}},
                    }
                ],
                "next_cursor": None,
                "has_more": False,
            },
        )

    async with _make_client(handler) as client:
        result = await client.pages.retrieve_property("page-123", "title")
        assert not isinstance(result, PropertyItem)
        items: list[PropertyItem] = []
        async for item in result:
            items.append(item)

    assert len(items) == 3
    assert len(calls) == 2
    assert calls[0] == {}
    assert calls[1] == {"start_cursor": "cursor-2"}


async def test_retrieve_property_page_forwards_pagination_params() -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["params"] = dict(request.url.params)
        return httpx.Response(
            200,
            json={
                "object": "list",
                "type": "property_item",
                "results": [],
                "next_cursor": None,
                "has_more": False,
            },
        )

    async with _make_client(handler) as client:
        await client.pages.retrieve_property_page(
            "page-123",
            "title",
            start_cursor="cur-x",
            page_size=5,
        )

    assert seen["params"] == {"start_cursor": "cur-x", "page_size": "5"}


async def test_client_exposes_pages_accessor() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_page_payload())

    async with _make_client(handler) as client:
        assert client.pages is not None
        # Sanity: call retrieve to confirm wiring.
        page = await client.pages.retrieve("page-123")
        assert page.id == "page-123"


async def test_retrieve_property_returns_async_iterator_type() -> None:
    """Smoke check that the iterator branch yields PropertyItem objects."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "object": "list",
                "type": "property_item",
                "results": [
                    {
                        "object": "property_item",
                        "id": "rel",
                        "type": "relation",
                        "relation": {"id": "abc"},
                    }
                ],
                "next_cursor": None,
                "has_more": False,
            },
        )

    async with _make_client(handler) as client:
        result = await client.pages.retrieve_property("page-123", "rel")
        assert not isinstance(result, PropertyItem)
        # mypy-style narrowing helper for human readability
        iterator: AsyncIterator[PropertyItem] = result
        items = [item async for item in iterator]

    assert len(items) == 1
    assert items[0].type == "relation"


@pytest.mark.parametrize("missing", ["properties", "children", "icon", "cover"])
async def test_create_omits_unspecified_fields(missing: str) -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json=_page_payload())

    async with _make_client(handler) as client:
        await client.pages.create(parent={"type": "page_id", "page_id": "p1"})

    assert missing not in seen["body"]
    assert seen["body"] == {"parent": {"type": "page_id", "page_id": "p1"}}
