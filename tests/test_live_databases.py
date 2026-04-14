"""Live integration tests for the Databases resource.

Skipped automatically when ``NOTION_TOKEN`` / ``NOTION_TEST_PAGE_ID`` are not
set. Every mutation is confined to descendants of ``NOTION_TEST_PAGE_ID``;
created databases and their child pages are archived in fixture teardown.
"""

from __future__ import annotations

from typing import Any

import pytest

from znotion import DatabaseObject, NotionClient, Page, PageObject

pytestmark = [pytest.mark.live, pytest.mark.asyncio(loop_scope="session")]


def _rich_text(content: str) -> list[dict[str, Any]]:
    return [{"type": "text", "text": {"content": content}}]


def _schema() -> dict[str, Any]:
    return {
        "Name": {"title": {}},
        "Notes": {"rich_text": {}},
        "Count": {"number": {"format": "number"}},
        "Tag": {
            "select": {
                "options": [
                    {"name": "alpha"},
                    {"name": "beta"},
                ],
            },
        },
        "Done": {"checkbox": {}},
        "When": {"date": {}},
    }


def _row_props(*, name: str, count: int, tag: str, done: bool, when: str) -> dict[str, Any]:
    return {
        "Name": {"title": _rich_text(name)},
        "Notes": {"rich_text": _rich_text(f"note for {name}")},
        "Count": {"number": count},
        "Tag": {"select": {"name": tag}},
        "Done": {"checkbox": done},
        "When": {"date": {"start": when}},
    }


async def test_databases_full_lifecycle(
    notion: NotionClient,
    test_page_id: str,
    created_databases: list[str],
    created_pages: list[str],
) -> None:
    """Create → retrieve → update → insert → query (filter+sort, paginated)."""
    created = await notion.databases.create(
        parent={"type": "page_id", "page_id": test_page_id},
        title=_rich_text("znotion live test db"),
        properties=_schema(),
        is_inline=True,
    )
    assert isinstance(created, DatabaseObject)
    assert created.id
    created_databases.append(created.id)
    assert created.is_inline is True
    assert set(created.properties).issuperset(
        {"Name", "Notes", "Count", "Tag", "Done", "When"},
    )

    fetched = await notion.databases.retrieve(created.id)
    assert isinstance(fetched, DatabaseObject)
    assert fetched.id == created.id

    updated = await notion.databases.update(
        created.id,
        title=_rich_text("znotion live test db (renamed)"),
        properties={"Extra": {"rich_text": {}}},
    )
    assert isinstance(updated, DatabaseObject)
    assert "Extra" in updated.properties
    assert updated.properties["Extra"].type == "rich_text"
    title_dump = [t.model_dump(mode="json", exclude_none=True) for t in updated.title]
    assert any("renamed" in (t.get("plain_text") or "") for t in title_dump)

    rows = [
        ("Row 1", 1, "alpha", False, "2026-01-01"),
        ("Row 2", 2, "beta", True, "2026-02-01"),
        ("Row 3", 3, "alpha", False, "2026-03-01"),
    ]
    inserted_ids: list[str] = []
    for name, count, tag, done, when in rows:
        page = await notion.pages.create(
            parent={"type": "database_id", "database_id": created.id},
            properties=_row_props(name=name, count=count, tag=tag, done=done, when=when),
        )
        assert isinstance(page, PageObject)
        inserted_ids.append(page.id)
        created_pages.append(page.id)
    assert len(inserted_ids) == 3

    query_filter = {"property": "Count", "number": {"greater_than_or_equal_to": 1}}
    query_sorts = [{"property": "Count", "direction": "ascending"}]

    iterated: list[PageObject] = []
    async for item in notion.databases.query(
        created.id,
        filter=query_filter,
        sorts=query_sorts,
    ):
        iterated.append(item)
    assert len(iterated) == 3
    counts = [p.properties["Count"].model_dump(mode="json", exclude_none=True) for p in iterated]
    assert [c.get("number") for c in counts] == [1, 2, 3]

    first_page = await notion.databases.query_page(
        created.id,
        filter=query_filter,
        sorts=query_sorts,
        page_size=2,
    )
    assert isinstance(first_page, Page)
    assert len(first_page.results) == 2
    assert first_page.has_more is True
    assert first_page.next_cursor is not None

    paginated: list[PageObject] = []
    async for item in notion.databases.query(
        created.id,
        filter=query_filter,
        sorts=query_sorts,
        page_size=2,
    ):
        paginated.append(item)
    assert len(paginated) == 3
    paginated_ids = [p.id for p in paginated]
    assert set(paginated_ids) == set(inserted_ids)
