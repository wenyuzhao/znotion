"""Page object and property item models."""

from typing import Literal

from pydantic import Field

from znotion.models.common import NotionModel, PartialUser
from znotion.models.files import Cover, Icon
from znotion.models.parent import Parent
from znotion.models.properties import PropertyValue


class PageObject(NotionModel):
    """Notion page object returned by the Pages and Databases endpoints."""

    object: Literal["page"] = "page"
    id: str
    created_time: str
    last_edited_time: str
    created_by: PartialUser | None = None
    last_edited_by: PartialUser | None = None
    cover: Cover | None = None
    icon: Icon | None = None
    parent: Parent
    is_archived: bool = False
    in_trash: bool = False
    is_locked: bool = False
    properties: dict[str, PropertyValue] = Field(default_factory=dict)
    url: str | None = None
    public_url: str | None = None


class PageMarkdown(NotionModel):
    """Markdown view of a page returned by the markdown endpoints.

    Shape: ``{"object": "page_markdown", "id": ..., "markdown": ...,
    "truncated": bool, "unknown_block_ids": [...]}``. File URIs embedded in
    ``markdown`` are pre-signed URLs when fetched from the Notion API.
    """

    object: Literal["page_markdown"] = "page_markdown"
    id: str
    markdown: str
    truncated: bool = False
    unknown_block_ids: list[str] = Field(default_factory=list)


class PropertyItem(NotionModel):
    """Single property item from ``GET /pages/{id}/properties/{property_id}``.

    Notion returns either a bare ``property_item`` object (for non-list
    property types like number/select/date) or, for list-valued types
    (title/rich_text/relation/people), a paginated list whose ``results`` are
    individual property items. Both shapes share the same per-item envelope
    modeled here. The type-specific value field (e.g. ``number``, ``select``,
    ``title``) is preserved via ``extra="allow"``.
    """

    object: Literal["property_item"] = "property_item"
    id: str | None = None
    type: str | None = None
    next_url: str | None = None
