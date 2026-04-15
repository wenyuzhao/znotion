"""Data Sources resource — wraps the ``/v1/data_sources`` endpoints.

Data sources replaced the inline database schema in Notion API ``2025-09-03``.
Use this resource to retrieve/update the property schema of a database and to
query rows (``POST /v1/data_sources/{id}/query``).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from pydantic import BaseModel

from znotion.http import Transport
from znotion.models.data_sources import DataSourceObject
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


class DataSourcesResource:
    """Methods for the Notion Data Sources API.

    Exposed on the client as ``client.data_sources``.
    """

    def __init__(self, transport: Transport) -> None:
        self._transport = transport

    async def create(
        self,
        *,
        parent: Any,
        properties: dict[str, Any],
        title: list[Any] | None = None,
        icon: Any | None = None,
    ) -> DataSourceObject:
        """Create a new data source on an existing database.

        ``parent`` must be a ``{"database_id": ...}`` reference.
        """
        body: dict[str, Any] = {
            "parent": _serialize(parent),
            "properties": _serialize_props(properties),
        }
        if title is not None:
            body["title"] = _serialize_rich_text(title)
        if icon is not None:
            body["icon"] = _serialize(icon)
        data = await self._transport.post("/data_sources", json=body)
        return DataSourceObject.model_validate(data)

    async def retrieve(self, data_source_id: str) -> DataSourceObject:
        data = await self._transport.get(f"/data_sources/{data_source_id}")
        return DataSourceObject.model_validate(data)

    async def update(
        self,
        data_source_id: str,
        *,
        title: list[Any] | None = None,
        properties: dict[str, Any] | None = None,
        icon: Any | None = None,
        in_trash: bool | None = None,
        parent: Any | None = None,
    ) -> DataSourceObject:
        body: dict[str, Any] = {}
        if title is not None:
            body["title"] = _serialize_rich_text(title)
        if properties is not None:
            body["properties"] = _serialize_props(properties)
        if icon is not None:
            body["icon"] = _serialize(icon)
        if in_trash is not None:
            body["in_trash"] = in_trash
        if parent is not None:
            body["parent"] = _serialize(parent)
        data = await self._transport.patch(
            f"/data_sources/{data_source_id}",
            json=body,
        )
        return DataSourceObject.model_validate(data)

    async def query_page(
        self,
        data_source_id: str,
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
            f"/data_sources/{data_source_id}/query",
            json=body,
        )
        return Page[PageObject].model_validate(data)

    def query(
        self,
        data_source_id: str,
        *,
        filter: dict[str, Any] | None = None,  # noqa: A002
        sorts: list[dict[str, Any]] | None = None,
        page_size: int | None = None,
    ) -> AsyncIterator[PageObject]:
        """Query a data source and auto-paginate the results.

        Returns an async iterator that walks every matching page. Use
        :meth:`query_page` if you want a single page and manual cursor control.
        """

        async def gen() -> AsyncIterator[PageObject]:
            cursor: str | None = None
            while True:
                page = await self.query_page(
                    data_source_id,
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
