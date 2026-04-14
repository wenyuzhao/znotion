"""Comments resource — wraps the ``/v1/comments`` endpoints."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from pydantic import BaseModel

from znotion.http import Transport
from znotion.models.comments import Comment
from znotion.pagination import Page


def _serialize(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json", exclude_none=True, by_alias=True)
    return value


def _serialize_rich_text(value: list[Any]) -> list[Any]:
    return [_serialize(v) for v in value]


class CommentsResource:
    """Methods for the Notion Comments API.

    Exposed on the client as ``client.comments``.
    """

    def __init__(self, transport: Transport) -> None:
        self._transport = transport

    async def create(
        self,
        *,
        rich_text: list[Any],
        parent: Any | None = None,
        discussion_id: str | None = None,
    ) -> Comment:
        """Create a comment on a page or reply to an existing discussion.

        Pass ``parent={"page_id": "..."}`` for a new page-level comment, or
        ``discussion_id="..."`` to reply to an existing thread. Exactly one
        of the two must be provided — the Notion API rejects requests that
        set both or neither.
        """
        body: dict[str, Any] = {"rich_text": _serialize_rich_text(rich_text)}
        if parent is not None:
            body["parent"] = _serialize(parent)
        if discussion_id is not None:
            body["discussion_id"] = discussion_id
        data = await self._transport.post("/comments", json=body)
        return Comment.model_validate(data)

    async def list_page(
        self,
        *,
        block_id: str,
        start_cursor: str | None = None,
        page_size: int | None = None,
    ) -> Page[Comment]:
        """Fetch a single page of comments for a block or page."""
        params: dict[str, Any] = {"block_id": block_id}
        if start_cursor is not None:
            params["start_cursor"] = start_cursor
        if page_size is not None:
            params["page_size"] = page_size
        data = await self._transport.get("/comments", params=params)
        return Page[Comment].model_validate(data)

    def list(
        self,
        *,
        block_id: str,
        page_size: int | None = None,
    ) -> AsyncIterator[Comment]:
        """List comments for a block or page, auto-paginating the results.

        Returns an async iterator that walks every comment. Use
        :meth:`list_page` if you want a single page and manual cursor control.
        """

        async def gen() -> AsyncIterator[Comment]:
            cursor: str | None = None
            while True:
                page = await self.list_page(
                    block_id=block_id,
                    start_cursor=cursor,
                    page_size=page_size,
                )
                for item in page.results:
                    yield item
                if not page.has_more or page.next_cursor is None:
                    return
                cursor = page.next_cursor

        return gen()
