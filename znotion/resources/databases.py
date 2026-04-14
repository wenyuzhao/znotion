"""Databases resource — wraps the ``/v1/databases`` endpoints."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from pydantic import BaseModel

from znotion.http import Transport
from znotion.models.databases import DatabaseObject
from znotion.models.pages import PageObject
from znotion.pagination import Page


def _serialize(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json", exclude_none=True, by_alias=True)
    return value


def _serialize_props(props: dict[str, Any]) -> dict[str, Any]:
    return {k: _serialize(v) for k, v in props.items()}


def _serialize_rich_text(value: Any) -> list[Any]:
    return [_serialize(v) for v in value]


class DatabasesResource:
    """Methods for the Notion Databases API.

    Exposed on the client as ``client.databases``.
    """

    def __init__(self, transport: Transport) -> None:
        self._transport = transport

    async def create(
        self,
        *,
        parent: Any,
        title: list[Any] | None = None,
        description: list[Any] | None = None,
        properties: dict[str, Any] | None = None,
        icon: Any | None = None,
        cover: Any | None = None,
        is_inline: bool | None = None,
    ) -> DatabaseObject:
        body: dict[str, Any] = {"parent": _serialize(parent)}
        if title is not None:
            body["title"] = _serialize_rich_text(title)
        if description is not None:
            body["description"] = _serialize_rich_text(description)
        if properties is not None:
            body["properties"] = _serialize_props(properties)
        if icon is not None:
            body["icon"] = _serialize(icon)
        if cover is not None:
            body["cover"] = _serialize(cover)
        if is_inline is not None:
            body["is_inline"] = is_inline
        data = await self._transport.post("/databases", json=body)
        return DatabaseObject.model_validate(data)

    async def retrieve(self, database_id: str) -> DatabaseObject:
        data = await self._transport.get(f"/databases/{database_id}")
        return DatabaseObject.model_validate(data)

    async def update(
        self,
        database_id: str,
        *,
        title: list[Any] | None = None,
        description: list[Any] | None = None,
        properties: dict[str, Any] | None = None,
        archived: bool | None = None,
        in_trash: bool | None = None,
        icon: Any | None = None,
        cover: Any | None = None,
        is_inline: bool | None = None,
    ) -> DatabaseObject:
        body: dict[str, Any] = {}
        if title is not None:
            body["title"] = _serialize_rich_text(title)
        if description is not None:
            body["description"] = _serialize_rich_text(description)
        if properties is not None:
            body["properties"] = _serialize_props(properties)
        if archived is not None:
            body["archived"] = archived
        if in_trash is not None:
            body["in_trash"] = in_trash
        if icon is not None:
            body["icon"] = _serialize(icon)
        if cover is not None:
            body["cover"] = _serialize(cover)
        if is_inline is not None:
            body["is_inline"] = is_inline
        data = await self._transport.patch(f"/databases/{database_id}", json=body)
        return DatabaseObject.model_validate(data)

    async def query_page(
        self,
        database_id: str,
        *,
        filter: dict[str, Any] | None = None,  # noqa: A002
        sorts: list[dict[str, Any]] | None = None,
        start_cursor: str | None = None,
        page_size: int | None = None,
    ) -> Page[PageObject]:
        body: dict[str, Any] = {}
        if filter is not None:
            body["filter"] = filter
        if sorts is not None:
            body["sorts"] = sorts
        if start_cursor is not None:
            body["start_cursor"] = start_cursor
        if page_size is not None:
            body["page_size"] = page_size
        data = await self._transport.post(
            f"/databases/{database_id}/query",
            json=body,
        )
        return Page[PageObject].model_validate(data)

    def query(
        self,
        database_id: str,
        *,
        filter: dict[str, Any] | None = None,  # noqa: A002
        sorts: list[dict[str, Any]] | None = None,
        page_size: int | None = None,
    ) -> AsyncIterator[PageObject]:
        """Query a database and auto-paginate the results.

        Returns an async iterator that walks every matching page. Use
        :meth:`query_page` if you want a single page and manual cursor control.
        """

        async def gen() -> AsyncIterator[PageObject]:
            cursor: str | None = None
            while True:
                page = await self.query_page(
                    database_id,
                    filter=filter,
                    sorts=sorts,
                    start_cursor=cursor,
                    page_size=page_size,
                )
                for item in page.results:
                    yield item
                if not page.has_more or page.next_cursor is None:
                    return
                cursor = page.next_cursor

        return gen()
