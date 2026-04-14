"""Live integration tests for the Comments resource.

Skipped automatically when ``NOTION_TOKEN`` / ``NOTION_TEST_PAGE_ID`` are not
set. Mutations are confined to a freshly-created child page; the
``created_pages`` fixture archives it on teardown.
"""

from __future__ import annotations

import pytest

from znotion import Comment, NotionClient

pytestmark = [pytest.mark.live, pytest.mark.asyncio(loop_scope="session")]


def _title_property(text: str) -> dict[str, list[dict[str, dict[str, str]]]]:
    return {"title": [{"text": {"content": text}}]}


def _rich_text(content: str) -> list[dict[str, dict[str, str]]]:
    return [{"text": {"content": content}}]


def _plain_text(comment: Comment) -> str:
    parts: list[str] = []
    for rt in comment.rich_text:
        dumped = rt.model_dump(mode="json", exclude_none=True)
        text = dumped.get("plain_text") or dumped.get("text", {}).get("content") or ""
        parts.append(text)
    return "".join(parts)


async def test_comments_full_lifecycle(
    notion: NotionClient,
    test_page_id: str,
    created_pages: list[str],
) -> None:
    """Create page → post comment → iterate → reply to discussion → verify."""
    parent = await notion.pages.create(
        parent={"type": "page_id", "page_id": test_page_id},
        properties={"title": _title_property("znotion live comments test")},
    )
    created_pages.append(parent.id)
    assert parent.id

    original_text = "znotion live comment"
    first = await notion.comments.create(
        parent={"page_id": parent.id},
        rich_text=_rich_text(original_text),
    )
    assert isinstance(first, Comment)
    assert first.id
    assert first.discussion_id
    assert _plain_text(first) == original_text

    listed_first = [c async for c in notion.comments.list(block_id=parent.id)]
    assert len(listed_first) >= 1
    assert all(isinstance(c, Comment) for c in listed_first)
    assert any(c.id == first.id for c in listed_first)
    matched = next(c for c in listed_first if c.id == first.id)
    assert _plain_text(matched) == original_text

    reply_text = "znotion live reply"
    reply = await notion.comments.create(
        discussion_id=first.discussion_id,
        rich_text=_rich_text(reply_text),
    )
    assert isinstance(reply, Comment)
    assert reply.discussion_id == first.discussion_id
    assert reply.id != first.id
    assert _plain_text(reply) == reply_text

    listed_after = [c async for c in notion.comments.list(block_id=parent.id)]
    ids_after = {c.id for c in listed_after}
    assert first.id in ids_after
    assert reply.id in ids_after

    reply_from_list = next(c for c in listed_after if c.id == reply.id)
    assert reply_from_list.discussion_id == first.discussion_id
    assert _plain_text(reply_from_list) == reply_text
