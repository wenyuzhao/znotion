"""Search resource — wraps the ``/v1/search`` endpoint.

In Notion ``2025-09-03+`` search results are pages or data sources, not
databases. The ``filter.value`` parameter accepts ``"page"`` or
``"data_source"``.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from znotion.http import Transport
from znotion.models.data_sources import DataSourceObject
from znotion.models.pages import PageObject
from znotion.models.search import SearchResult
from znotion.pagination import Page


class SearchResource:
    """Methods for the Notion Search API.

    Exposed on the client as ``client.search``.
    """

    def __init__(self, transport: Transport) -> None:
        self._transport = transport

    async def search_page(
        self,
        *,
        query: str | None = None,
        filter: dict[str, Any] | None = None,  # noqa: A002
        sort: dict[str, Any] | None = None,
        start_cursor: str | None = None,
        page_size: int | None = None,
    ) -> Page[PageObject | DataSourceObject]:
        """Fetch a single page of search results."""
        body: dict[str, Any] = {}
        if query is not None:
            body["query"] = query
        if filter is not None:
            body["filter"] = filter
        if sort is not None:
            body["sort"] = sort
        if start_cursor is not None:
            body["start_cursor"] = start_cursor
        if page_size is not None:
            body["page_size"] = page_size
        data = await self._transport.post("/search", json=body)
        return Page[SearchResult].model_validate(data)

    def search(
        self,
        *,
        query: str | None = None,
        filter: dict[str, Any] | None = None,  # noqa: A002
        sort: dict[str, Any] | None = None,
        page_size: int | None = None,
    ) -> AsyncIterator[PageObject | DataSourceObject]:
        """Search across pages and data sources, auto-paginating the results.

        Returns an async iterator that walks every matching page or data
        source. Use :meth:`search_page` if you want a single page and manual
        cursor control.
        """

        async def gen() -> AsyncIterator[PageObject | DataSourceObject]:
            cursor: str | None = None
            while True:
                page = await self.search_page(
                    query=query,
                    filter=filter,
                    sort=sort,
                    start_cursor=cursor,
                    page_size=page_size,
                )
                for item in page.results:
                    yield item
                if not page.has_more or page.next_cursor is None:
                    return
                cursor = page.next_cursor

        return gen()
