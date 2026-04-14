"""Pages resource — wraps the ``/v1/pages`` endpoints."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from pydantic import BaseModel

from znotion.http import Transport
from znotion.models.pages import PageObject, PropertyItem
from znotion.pagination import Page


def _serialize(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json", exclude_none=True, by_alias=True)
    return value


def _serialize_props(props: dict[str, Any]) -> dict[str, Any]:
    return {k: _serialize(v) for k, v in props.items()}


class PagesResource:
    """Methods for the Notion Pages API.

    Exposed on the client as ``client.pages``.
    """

    def __init__(self, transport: Transport) -> None:
        self._transport = transport

    async def create(
        self,
        *,
        parent: Any,
        properties: dict[str, Any] | None = None,
        children: list[Any] | None = None,
        icon: Any | None = None,
        cover: Any | None = None,
    ) -> PageObject:
        body: dict[str, Any] = {"parent": _serialize(parent)}
        if properties is not None:
            body["properties"] = _serialize_props(properties)
        if children is not None:
            body["children"] = [_serialize(c) for c in children]
        if icon is not None:
            body["icon"] = _serialize(icon)
        if cover is not None:
            body["cover"] = _serialize(cover)
        data = await self._transport.post("/pages", json=body)
        return PageObject.model_validate(data)

    async def retrieve(self, page_id: str) -> PageObject:
        data = await self._transport.get(f"/pages/{page_id}")
        return PageObject.model_validate(data)

    async def update(
        self,
        page_id: str,
        *,
        properties: dict[str, Any] | None = None,
        archived: bool | None = None,
        in_trash: bool | None = None,
        icon: Any | None = None,
        cover: Any | None = None,
    ) -> PageObject:
        body: dict[str, Any] = {}
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
        data = await self._transport.patch(f"/pages/{page_id}", json=body)
        return PageObject.model_validate(data)

    async def _fetch_property_raw(
        self,
        page_id: str,
        property_id: str,
        *,
        start_cursor: str | None = None,
        page_size: int | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if start_cursor is not None:
            params["start_cursor"] = start_cursor
        if page_size is not None:
            params["page_size"] = page_size
        return await self._transport.get(
            f"/pages/{page_id}/properties/{property_id}",
            params=params or None,
        )

    async def retrieve_property_page(
        self,
        page_id: str,
        property_id: str,
        *,
        start_cursor: str | None = None,
        page_size: int | None = None,
    ) -> Page[PropertyItem] | PropertyItem:
        """Fetch a single page of a property item response.

        Returns a ``Page[PropertyItem]`` for list-valued properties (title,
        rich_text, relation, people) and a bare ``PropertyItem`` for all
        other types.
        """
        data = await self._fetch_property_raw(
            page_id,
            property_id,
            start_cursor=start_cursor,
            page_size=page_size,
        )
        if data.get("object") == "list":
            return Page[PropertyItem].model_validate(data)
        return PropertyItem.model_validate(data)

    async def retrieve_property(
        self,
        page_id: str,
        property_id: str,
    ) -> PropertyItem | AsyncIterator[PropertyItem]:
        """Retrieve a page property, auto-paginating list-valued types.

        For list-valued properties (e.g. ``title``, ``rich_text``,
        ``relation``, ``people``) returns an async iterator that walks every
        page. For non-list types returns the single ``PropertyItem`` directly.
        """
        first_raw = await self._fetch_property_raw(page_id, property_id)
        if first_raw.get("object") == "list":
            first_page = Page[PropertyItem].model_validate(first_raw)
            return self._iter_property(page_id, property_id, first_page)
        return PropertyItem.model_validate(first_raw)

    def _iter_property(
        self,
        page_id: str,
        property_id: str,
        first: Page[PropertyItem],
    ) -> AsyncIterator[PropertyItem]:
        async def gen() -> AsyncIterator[PropertyItem]:
            page = first
            while True:
                for item in page.results:
                    yield item
                if not page.has_more or page.next_cursor is None:
                    return
                next_raw = await self._fetch_property_raw(
                    page_id,
                    property_id,
                    start_cursor=page.next_cursor,
                )
                page = Page[PropertyItem].model_validate(next_raw)

        return gen()
