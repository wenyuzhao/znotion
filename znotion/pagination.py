"""Pagination helpers for Notion list endpoints."""

from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

from znotion.models.common import NotionModel


class Page[T](NotionModel):
    """A single page of results from a Notion list endpoint."""

    object: str = "list"
    results: list[T]
    next_cursor: str | None = None
    has_more: bool = False
    type: str | None = None


async def paginate[T](
    fetch_page: Callable[..., Awaitable[Page[T]]],
    *,
    page_size: int | None = None,
    **kwargs: Any,
) -> AsyncIterator[T]:
    """Iterate every item across all pages of a Notion list endpoint.

    `fetch_page` must accept `start_cursor` as a keyword argument and return a
    `Page[T]`. Extra `**kwargs` are forwarded unchanged to each call, along
    with `page_size` when provided. Iteration stops once a page reports
    `has_more=False` or returns no `next_cursor`.
    """
    cursor: str | None = None
    while True:
        call_kwargs: dict[str, Any] = dict(kwargs)
        call_kwargs["start_cursor"] = cursor
        if page_size is not None:
            call_kwargs["page_size"] = page_size
        page = await fetch_page(**call_kwargs)
        for item in page.results:
            yield item
        if not page.has_more or page.next_cursor is None:
            return
        cursor = page.next_cursor
