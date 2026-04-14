"""Unit tests for znotion.resources.blocks.BlocksResource and Block models."""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from znotion import Block, NotionClient, Page
from znotion.models.blocks import (
    GenericBlock,
    Heading1Block,
    ParagraphBlock,
    block_adapter,
)


def _block_payload(
    *,
    block_id: str = "block-1",
    block_type: str = "paragraph",
    inner: dict[str, Any] | None = None,
    has_children: bool = False,
) -> dict[str, Any]:
    return {
        "object": "block",
        "id": block_id,
        "parent": {"type": "page_id", "page_id": "page-1"},
        "created_time": "2024-01-01T00:00:00.000Z",
        "last_edited_time": "2024-01-02T00:00:00.000Z",
        "created_by": {"object": "user", "id": "u1"},
        "last_edited_by": {"object": "user", "id": "u2"},
        "archived": False,
        "in_trash": False,
        "has_children": has_children,
        "type": block_type,
        block_type: inner or {},
    }


def _make_client(handler: Any) -> NotionClient:
    return NotionClient(token="secret_test", transport=httpx.MockTransport(handler))


# ---------------------------------------------------------------------------
# Block model dispatch
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("block_type", "cls_name"),
    [
        ("paragraph", "ParagraphBlock"),
        ("heading_1", "Heading1Block"),
        ("heading_2", "Heading2Block"),
        ("bulleted_list_item", "BulletedListItemBlock"),
        ("to_do", "ToDoBlock"),
        ("code", "CodeBlock"),
        ("divider", "DividerBlock"),
        ("table_of_contents", "TableOfContentsBlock"),
        ("table_row", "TableRowBlock"),
        ("image", "ImageBlock"),
        ("equation", "EquationBlock"),
        ("synced_block", "SyncedBlock"),
        ("child_database", "ChildDatabaseBlock"),
        ("link_preview", "LinkPreviewBlock"),
        ("unsupported", "UnsupportedBlock"),
    ],
)
def test_block_discriminator_routes_known_types(block_type: str, cls_name: str) -> None:
    payload = _block_payload(block_type=block_type, inner={"foo": "bar"})
    parsed = block_adapter.validate_python(payload)
    assert type(parsed).__name__ == cls_name
    assert parsed.type == block_type


def test_block_discriminator_falls_back_to_generic_for_unknown_type() -> None:
    payload = _block_payload(block_type="future_thing", inner={"x": 1})
    parsed = block_adapter.validate_python(payload)
    assert isinstance(parsed, GenericBlock)
    assert parsed.type == "future_thing"
    dumped = parsed.model_dump(exclude_unset=True)
    assert dumped["type"] == "future_thing"
    assert dumped["future_thing"] == {"x": 1}


def test_block_round_trips_through_adapter() -> None:
    payload = _block_payload(
        block_type="paragraph",
        inner={"rich_text": [], "color": "default"},
    )
    parsed = block_adapter.validate_python(payload)
    redumped = block_adapter.dump_python(parsed, exclude_unset=True)
    re_parsed = block_adapter.validate_python(redumped)
    assert re_parsed == parsed


def test_paragraph_block_preserves_inner_dict() -> None:
    payload = _block_payload(
        block_type="paragraph",
        inner={"rich_text": [{"type": "text", "text": {"content": "hello"}}]},
    )
    parsed = block_adapter.validate_python(payload)
    assert isinstance(parsed, ParagraphBlock)
    assert parsed.paragraph["rich_text"][0]["text"]["content"] == "hello"


# ---------------------------------------------------------------------------
# Resource methods
# ---------------------------------------------------------------------------


async def test_retrieve_returns_typed_block() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/v1/blocks/block-1"
        return httpx.Response(200, json=_block_payload(block_type="heading_1"))

    async with _make_client(handler) as client:
        block = await client.blocks.retrieve("block-1")

    assert isinstance(block, Heading1Block)
    assert block.id == "block-1"


async def test_retrieve_returns_generic_block_for_unknown_type() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=_block_payload(block_type="future_widget", inner={"foo": "bar"}),
        )

    async with _make_client(handler) as client:
        block = await client.blocks.retrieve("block-1")

    assert isinstance(block, GenericBlock)
    assert block.type == "future_widget"


async def test_update_patches_with_provided_fields() -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["path"] = request.url.path
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json=_block_payload(block_type="paragraph"))

    async with _make_client(handler) as client:
        block = await client.blocks.update(
            "block-1",
            paragraph={"rich_text": [{"type": "text", "text": {"content": "x"}}]},
            archived=False,
        )

    assert seen["method"] == "PATCH"
    assert seen["path"] == "/v1/blocks/block-1"
    assert seen["body"] == {
        "paragraph": {"rich_text": [{"type": "text", "text": {"content": "x"}}]},
        "archived": False,
    }
    assert isinstance(block, ParagraphBlock)


async def test_update_with_no_fields_sends_empty_body() -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json=_block_payload())

    async with _make_client(handler) as client:
        await client.blocks.update("block-1")

    assert seen["body"] == {}


async def test_delete_calls_correct_method_and_path() -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["path"] = request.url.path
        return httpx.Response(
            200,
            json=_block_payload(block_type="paragraph"),
        )

    async with _make_client(handler) as client:
        block = await client.blocks.delete("block-1")

    assert seen["method"] == "DELETE"
    assert seen["path"] == "/v1/blocks/block-1"
    assert isinstance(block, ParagraphBlock)


async def test_children_page_forwards_pagination_params() -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["path"] = request.url.path
        seen["params"] = dict(request.url.params)
        return httpx.Response(
            200,
            json={
                "object": "list",
                "type": "block",
                "results": [_block_payload(block_id="c1", block_type="divider")],
                "next_cursor": None,
                "has_more": False,
            },
        )

    async with _make_client(handler) as client:
        page = await client.blocks.children_page(
            "block-1",
            start_cursor="cur-x",
            page_size=10,
        )

    assert seen["method"] == "GET"
    assert seen["path"] == "/v1/blocks/block-1/children"
    assert seen["params"] == {"start_cursor": "cur-x", "page_size": "10"}
    assert isinstance(page, Page)
    assert len(page.results) == 1
    assert page.results[0].id == "c1"


async def test_children_page_omits_unset_params() -> None:
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
        await client.blocks.children_page("block-1")

    assert seen["params"] == {}


async def test_children_auto_paginates_across_pages() -> None:
    calls: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(dict(request.url.params))
        if request.url.params.get("start_cursor") is None:
            return httpx.Response(
                200,
                json={
                    "object": "list",
                    "results": [
                        _block_payload(block_id="c1", block_type="paragraph"),
                        _block_payload(block_id="c2", block_type="divider"),
                    ],
                    "next_cursor": "cursor-2",
                    "has_more": True,
                },
            )
        return httpx.Response(
            200,
            json={
                "object": "list",
                "results": [
                    _block_payload(block_id="c3", block_type="heading_1"),
                ],
                "next_cursor": None,
                "has_more": False,
            },
        )

    async with _make_client(handler) as client:
        items: list[Block] = []
        async for block in client.blocks.children("block-1"):
            items.append(block)

    assert [b.id for b in items] == ["c1", "c2", "c3"]
    assert len(calls) == 2
    assert calls[0] == {}
    assert calls[1] == {"start_cursor": "cursor-2"}


async def test_children_stops_when_has_more_is_false() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "object": "list",
                "results": [_block_payload(block_id="only", block_type="divider")],
                "next_cursor": "stale-cursor",
                "has_more": False,
            },
        )

    async with _make_client(handler) as client:
        items = [b async for b in client.blocks.children("block-1")]

    assert len(items) == 1
    assert items[0].id == "only"


async def test_children_forwards_page_size() -> None:
    seen: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(dict(request.url.params))
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
        async for _ in client.blocks.children("block-1", page_size=25):
            pass

    assert seen == [{"page_size": "25"}]


async def test_append_children_posts_body_with_after() -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["path"] = request.url.path
        seen["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "object": "list",
                "results": [_block_payload(block_id="new", block_type="paragraph")],
                "next_cursor": None,
                "has_more": False,
            },
        )

    async with _make_client(handler) as client:
        result = await client.blocks.append_children(
            "block-1",
            children=[
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {"rich_text": []},
                }
            ],
            after="sibling-id",
        )

    assert seen["method"] == "PATCH"
    assert seen["path"] == "/v1/blocks/block-1/children"
    assert seen["body"]["children"][0]["type"] == "paragraph"
    assert seen["body"]["after"] == "sibling-id"
    assert isinstance(result, Page)
    assert result.results[0].id == "new"


async def test_append_children_omits_after_when_unset() -> None:
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
        await client.blocks.append_children(
            "block-1",
            children=[{"type": "divider", "divider": {}}],
        )

    assert "after" not in seen["body"]
    assert seen["body"]["children"] == [{"type": "divider", "divider": {}}]


async def test_client_exposes_blocks_accessor() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_block_payload())

    async with _make_client(handler) as client:
        assert client.blocks is not None
        block = await client.blocks.retrieve("block-1")
        assert block.id == "block-1"
