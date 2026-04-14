"""Blocks resource — wraps the ``/v1/blocks`` endpoints."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from pydantic import BaseModel

from znotion.http import Transport
from znotion.models.blocks import Block, block_adapter
from znotion.pagination import Page


def _serialize(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json", exclude_none=True, by_alias=True)
    return value


class BlocksResource:
    """Methods for the Notion Blocks API.

    Exposed on the client as ``client.blocks``.
    """

    def __init__(self, transport: Transport) -> None:
        self._transport = transport

    async def retrieve(self, block_id: str) -> Block:
        data = await self._transport.get(f"/blocks/{block_id}")
        return block_adapter.validate_python(data)

    async def update(self, block_id: str, **fields: Any) -> Block:
        body = {key: _serialize(value) for key, value in fields.items()}
        data = await self._transport.patch(f"/blocks/{block_id}", json=body)
        return block_adapter.validate_python(data)

    async def delete(self, block_id: str) -> Block:
        data = await self._transport.delete(f"/blocks/{block_id}")
        return block_adapter.validate_python(data)

    async def children_page(
        self,
        block_id: str,
        *,
        start_cursor: str | None = None,
        page_size: int | None = None,
    ) -> Page[Block]:
        params: dict[str, Any] = {}
        if start_cursor is not None:
            params["start_cursor"] = start_cursor
        if page_size is not None:
            params["page_size"] = page_size
        data = await self._transport.get(
            f"/blocks/{block_id}/children",
            params=params or None,
        )
        return Page[Block].model_validate(data)

    def children(
        self,
        block_id: str,
        *,
        page_size: int | None = None,
    ) -> AsyncIterator[Block]:
        """Iterate every child block, auto-paginating across pages."""

        async def gen() -> AsyncIterator[Block]:
            cursor: str | None = None
            while True:
                page = await self.children_page(
                    block_id,
                    start_cursor=cursor,
                    page_size=page_size,
                )
                for item in page.results:
                    yield item
                if not page.has_more or page.next_cursor is None:
                    return
                cursor = page.next_cursor

        return gen()

    async def append_children(
        self,
        block_id: str,
        *,
        children: list[Any],
        after: str | None = None,
    ) -> Page[Block]:
        body: dict[str, Any] = {"children": [_serialize(c) for c in children]}
        if after is not None:
            body["after"] = after
        data = await self._transport.patch(
            f"/blocks/{block_id}/children",
            json=body,
        )
        return Page[Block].model_validate(data)
