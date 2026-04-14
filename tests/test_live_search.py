"""Live integration tests for the Search resource.

Skipped automatically when ``NOTION_TOKEN`` / ``NOTION_TEST_PAGE_ID`` are not
set. Creates a uniquely-titled child page under the test page and exercises
both the unfiltered iterator and the ``{"property": "object", "value":
"database"}`` filter. Notion's search index is eventually consistent, so the
query-title lookup retries for a bounded window and emits a warning (rather
than failing) if the page never appears.
"""

from __future__ import annotations

import asyncio
import uuid
import warnings

import pytest

from znotion import DatabaseObject, NotionClient, PageObject

pytestmark = [pytest.mark.live, pytest.mark.asyncio(loop_scope="session")]

_INDEX_RETRIES = 10
_INDEX_DELAY_SECONDS = 3.0
_FILTER_SCAN_LIMIT = 50


def _title_property(text: str) -> dict[str, list[dict[str, dict[str, str]]]]:
    return {"title": [{"text": {"content": text}}]}


async def test_search_finds_created_page_by_unique_title(
    notion: NotionClient,
    test_page_id: str,
    created_pages: list[str],
) -> None:
    """Create a child page with a unique title and look it up via search."""
    unique_title = f"znotion-search-{uuid.uuid4().hex[:12]}"
    created = await notion.pages.create(
        parent={"type": "page_id", "page_id": test_page_id},
        properties={"title": _title_property(unique_title)},
    )
    created_pages.append(created.id)

    found: PageObject | None = None
    for attempt in range(_INDEX_RETRIES):
        async for result in notion.search.search(query=unique_title, page_size=25):
            if isinstance(result, PageObject) and result.id == created.id:
                found = result
                break
        if found is not None:
            break
        if attempt < _INDEX_RETRIES - 1:
            await asyncio.sleep(_INDEX_DELAY_SECONDS)

    if found is None:
        warnings.warn(
            f"Notion search did not index {unique_title!r} within "
            f"{_INDEX_RETRIES * _INDEX_DELAY_SECONDS:.0f}s; tolerating lag.",
            stacklevel=1,
        )
        return

    assert found.id == created.id
    assert found.object == "page"


async def test_search_filter_databases_only_returns_databases(
    notion: NotionClient,
    test_page_id: str,
) -> None:
    """The ``object=database`` filter must only yield ``DatabaseObject`` results."""
    # Sanity check the single-page form as well — it should return
    # ``Page[PageObject | DatabaseObject]`` but every ``results`` element
    # should be a database when the filter is set.
    single = await notion.search.search_page(
        filter={"property": "object", "value": "database"},
        page_size=10,
    )
    for result in single.results:
        assert isinstance(result, DatabaseObject)
        assert result.object == "database"

    seen = 0
    async for result in notion.search.search(
        filter={"property": "object", "value": "database"},
        page_size=10,
    ):
        assert isinstance(result, DatabaseObject)
        assert result.object == "database"
        seen += 1
        if seen >= _FILTER_SCAN_LIMIT:
            break
    # We don't assert seen > 0 — the workspace might legitimately contain no
    # databases the integration can see. The type invariant is what matters.
    assert test_page_id  # keep fixture dependency explicit
