"""Databases resource — wraps the ``/v1/databases`` endpoints.

In Notion API ``2025-09-03+`` databases became thin containers for one or
more *data sources*, and the property schema / query endpoints moved to the
:class:`~znotion.resources.data_sources.DataSourcesResource`. This resource
only covers database create/retrieve/update; use ``client.data_sources`` for
schema and query operations.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from znotion.http import Transport
from znotion.models.databases import DatabaseObject


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
        """Create a database.

        ``properties`` is the initial data source schema — it is wrapped
        under ``initial_data_source.properties`` as required by Notion
        ``2025-09-03+``.
        """
        body: dict[str, Any] = {"parent": _serialize(parent)}
        if title is not None:
            body["title"] = _serialize_rich_text(title)
        if description is not None:
            body["description"] = _serialize_rich_text(description)
        if properties is not None:
            body["initial_data_source"] = {
                "properties": _serialize_props(properties),
            }
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
        in_trash: bool | None = None,
        icon: Any | None = None,
        cover: Any | None = None,
        is_inline: bool | None = None,
        is_locked: bool | None = None,
    ) -> DatabaseObject:
        """Update database-level attributes.

        Schema (``properties``) edits now live on the data source; use
        ``client.data_sources.update(data_source_id, properties=...)``.
        """
        body: dict[str, Any] = {}
        if title is not None:
            body["title"] = _serialize_rich_text(title)
        if description is not None:
            body["description"] = _serialize_rich_text(description)
        if in_trash is not None:
            body["in_trash"] = in_trash
        if icon is not None:
            body["icon"] = _serialize(icon)
        if cover is not None:
            body["cover"] = _serialize(cover)
        if is_inline is not None:
            body["is_inline"] = is_inline
        if is_locked is not None:
            body["is_locked"] = is_locked
        data = await self._transport.patch(f"/databases/{database_id}", json=body)
        return DatabaseObject.model_validate(data)
