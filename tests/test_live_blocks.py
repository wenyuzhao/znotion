"""Live integration tests for the Blocks resource.

Skipped automatically when ``NOTION_TOKEN`` / ``NOTION_TEST_PAGE_ID`` are not
set. Mutations are confined to a freshly-created child page; the
``created_pages`` fixture archives it on teardown.
"""

from __future__ import annotations

import pytest

from znotion import NotionClient
from znotion.models.blocks import (
    BulletedListItemBlock,
    CodeBlock,
    DividerBlock,
    Heading1Block,
    ParagraphBlock,
    ToDoBlock,
)

pytestmark = [pytest.mark.live, pytest.mark.asyncio(loop_scope="session")]


def _title_property(text: str) -> dict[str, list[dict[str, dict[str, str]]]]:
    return {"title": [{"text": {"content": text}}]}


def _rich_text(content: str) -> list[dict[str, dict[str, str]]]:
    return [{"text": {"content": content}}]


async def test_blocks_full_lifecycle(
    notion: NotionClient,
    test_page_id: str,
    created_pages: list[str],
) -> None:
    """Append → list (paginated) → update → delete blocks on a child page."""
    parent = await notion.pages.create(
        parent={"type": "page_id", "page_id": test_page_id},
        properties={"title": _title_property("znotion live blocks test")},
    )
    created_pages.append(parent.id)
    assert parent.id

    children_payload = [
        {"type": "paragraph", "paragraph": {"rich_text": _rich_text("p-one")}},
        {"type": "heading_1", "heading_1": {"rich_text": _rich_text("h-one")}},
        {
            "type": "bulleted_list_item",
            "bulleted_list_item": {"rich_text": _rich_text("b-one")},
        },
        {
            "type": "to_do",
            "to_do": {"rich_text": _rich_text("todo-one"), "checked": False},
        },
        {
            "type": "code",
            "code": {"rich_text": _rich_text("print('hi')"), "language": "python"},
        },
        {"type": "divider", "divider": {}},
    ]
    appended = await notion.blocks.append_children(parent.id, children=children_payload)
    assert len(appended.results) == 6

    listed = [block async for block in notion.blocks.children(parent.id, page_size=2)]
    assert len(listed) == 6

    expected_classes = [
        ParagraphBlock,
        Heading1Block,
        BulletedListItemBlock,
        ToDoBlock,
        CodeBlock,
        DividerBlock,
    ]
    for block, cls in zip(listed, expected_classes, strict=True):
        assert isinstance(block, cls)

    paragraph_id = listed[0].id
    assert paragraph_id is not None
    updated = await notion.blocks.update(
        paragraph_id,
        paragraph={"rich_text": _rich_text("p-one (edited)")},
    )
    assert isinstance(updated, ParagraphBlock)

    refetched = await notion.blocks.retrieve(paragraph_id)
    assert isinstance(refetched, ParagraphBlock)
    paragraph_data = refetched.model_dump(mode="json", exclude_none=True)["paragraph"]
    rich_text = paragraph_data["rich_text"]
    assert any("edited" in (rt.get("plain_text") or "") for rt in rich_text)

    divider_id = listed[-1].id
    assert divider_id is not None
    deleted = await notion.blocks.delete(divider_id)
    assert isinstance(deleted, DividerBlock)

    after_delete = [block async for block in notion.blocks.children(parent.id, page_size=2)]
    divider_after = next((b for b in after_delete if b.id == divider_id), None)
    assert divider_after is None or divider_after.archived is True
