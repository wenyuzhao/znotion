"""Live integration tests for the Pages resource.

Skipped automatically when ``NOTION_TOKEN`` / ``NOTION_TEST_PAGE_ID`` are not
set. Every mutation is confined to descendants of ``NOTION_TEST_PAGE_ID`` and
the ``created_pages`` fixture archives anything created during the test.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest

from znotion import NotionClient, PageObject, PropertyItem

pytestmark = [pytest.mark.live, pytest.mark.asyncio(loop_scope="session")]


def _title_property(text: str) -> dict[str, list[dict[str, dict[str, str]]]]:
    return {"title": [{"text": {"content": text}}]}


async def test_pages_full_lifecycle(
    notion: NotionClient,
    test_page_id: str,
    created_pages: list[str],
) -> None:
    """Create → retrieve → update title+icon → archive a child page."""
    created = await notion.pages.create(
        parent={"type": "page_id", "page_id": test_page_id},
        properties={"title": _title_property("znotion live test page")},
        icon={"type": "emoji", "emoji": "🧪"},
    )
    assert isinstance(created, PageObject)
    assert created.id
    created_pages.append(created.id)
    assert created.archived is False
    assert created.icon is not None

    fetched = await notion.pages.retrieve(created.id)
    assert isinstance(fetched, PageObject)
    assert fetched.id == created.id
    assert "title" in fetched.properties

    updated = await notion.pages.update(
        created.id,
        properties={"title": _title_property("znotion live test page (renamed)")},
        icon={"type": "emoji", "emoji": "✅"},
    )
    assert isinstance(updated, PageObject)
    assert updated.id == created.id
    assert updated.icon is not None
    updated_icon = updated.icon.model_dump(mode="json", exclude_none=True)
    assert updated_icon.get("emoji") == "✅"

    archived = await notion.pages.update(created.id, archived=True)
    assert isinstance(archived, PageObject)
    assert archived.archived is True


async def test_pages_retrieve_property_title(
    notion: NotionClient,
    test_page_id: str,
    created_pages: list[str],
) -> None:
    """Retrieve the ``title`` property both via ``retrieve_property_page``
    and via the auto-paginating iterator form."""
    created = await notion.pages.create(
        parent={"type": "page_id", "page_id": test_page_id},
        properties={"title": _title_property("znotion property fetch test")},
    )
    created_pages.append(created.id)

    title_prop_id = created.properties["title"].id
    assert title_prop_id is not None

    page = await notion.pages.retrieve_property_page(created.id, title_prop_id)
    from znotion import Page as PageType

    assert isinstance(page, PageType)
    assert len(page.results) >= 1
    assert all(isinstance(item, PropertyItem) for item in page.results)

    iter_or_item = await notion.pages.retrieve_property(created.id, title_prop_id)
    assert isinstance(iter_or_item, AsyncIterator)
    items = [item async for item in iter_or_item]
    assert len(items) >= 1
    assert all(isinstance(item, PropertyItem) for item in items)
