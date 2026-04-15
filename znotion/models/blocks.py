"""Block object models — discriminated union over Notion's block types.

Notion documents 30+ block types. Each is modeled as a thin leaf class with a
``type`` literal and a single type-specific data field. The data field is
typed as ``dict[str, Any]`` to keep the file compact and forward-compatible —
unknown fields round-trip through ``extra="allow"`` regardless. ``Block`` is a
discriminated union with a callable discriminator that routes any unknown
``type`` value to ``GenericBlock`` for graceful forward compatibility.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import Discriminator, Field, Tag, TypeAdapter

from znotion.models.common import NotionModel, PartialUser
from znotion.models.parent import Parent


class _BlockBase(NotionModel):
    """Shared envelope fields for every block type."""

    object: Literal["block"] = "block"
    id: str | None = None
    parent: Parent | None = None
    created_time: str | None = None
    last_edited_time: str | None = None
    created_by: PartialUser | None = None
    last_edited_by: PartialUser | None = None
    in_trash: bool = False
    has_children: bool = False


class ParagraphBlock(_BlockBase):
    type: Literal["paragraph"] = "paragraph"
    paragraph: dict[str, Any] = Field(default_factory=dict)


class Heading1Block(_BlockBase):
    type: Literal["heading_1"] = "heading_1"
    heading_1: dict[str, Any] = Field(default_factory=dict)


class Heading2Block(_BlockBase):
    type: Literal["heading_2"] = "heading_2"
    heading_2: dict[str, Any] = Field(default_factory=dict)


class Heading3Block(_BlockBase):
    type: Literal["heading_3"] = "heading_3"
    heading_3: dict[str, Any] = Field(default_factory=dict)


class BulletedListItemBlock(_BlockBase):
    type: Literal["bulleted_list_item"] = "bulleted_list_item"
    bulleted_list_item: dict[str, Any] = Field(default_factory=dict)


class NumberedListItemBlock(_BlockBase):
    type: Literal["numbered_list_item"] = "numbered_list_item"
    numbered_list_item: dict[str, Any] = Field(default_factory=dict)


class ToDoBlock(_BlockBase):
    type: Literal["to_do"] = "to_do"
    to_do: dict[str, Any] = Field(default_factory=dict)


class ToggleBlock(_BlockBase):
    type: Literal["toggle"] = "toggle"
    toggle: dict[str, Any] = Field(default_factory=dict)


class QuoteBlock(_BlockBase):
    type: Literal["quote"] = "quote"
    quote: dict[str, Any] = Field(default_factory=dict)


class CalloutBlock(_BlockBase):
    type: Literal["callout"] = "callout"
    callout: dict[str, Any] = Field(default_factory=dict)


class CodeBlock(_BlockBase):
    type: Literal["code"] = "code"
    code: dict[str, Any] = Field(default_factory=dict)


class DividerBlock(_BlockBase):
    type: Literal["divider"] = "divider"
    divider: dict[str, Any] = Field(default_factory=dict)


class BreadcrumbBlock(_BlockBase):
    type: Literal["breadcrumb"] = "breadcrumb"
    breadcrumb: dict[str, Any] = Field(default_factory=dict)


class TableOfContentsBlock(_BlockBase):
    type: Literal["table_of_contents"] = "table_of_contents"
    table_of_contents: dict[str, Any] = Field(default_factory=dict)


class ColumnListBlock(_BlockBase):
    type: Literal["column_list"] = "column_list"
    column_list: dict[str, Any] = Field(default_factory=dict)


class ColumnBlock(_BlockBase):
    type: Literal["column"] = "column"
    column: dict[str, Any] = Field(default_factory=dict)


class LinkToPageBlock(_BlockBase):
    type: Literal["link_to_page"] = "link_to_page"
    link_to_page: dict[str, Any] = Field(default_factory=dict)


class TableBlock(_BlockBase):
    type: Literal["table"] = "table"
    table: dict[str, Any] = Field(default_factory=dict)


class TableRowBlock(_BlockBase):
    type: Literal["table_row"] = "table_row"
    table_row: dict[str, Any] = Field(default_factory=dict)


class EmbedBlock(_BlockBase):
    type: Literal["embed"] = "embed"
    embed: dict[str, Any] = Field(default_factory=dict)


class BookmarkBlock(_BlockBase):
    type: Literal["bookmark"] = "bookmark"
    bookmark: dict[str, Any] = Field(default_factory=dict)


class ImageBlock(_BlockBase):
    type: Literal["image"] = "image"
    image: dict[str, Any] = Field(default_factory=dict)


class VideoBlock(_BlockBase):
    type: Literal["video"] = "video"
    video: dict[str, Any] = Field(default_factory=dict)


class PdfBlock(_BlockBase):
    type: Literal["pdf"] = "pdf"
    pdf: dict[str, Any] = Field(default_factory=dict)


class FileBlock(_BlockBase):
    type: Literal["file"] = "file"
    file: dict[str, Any] = Field(default_factory=dict)


class AudioBlock(_BlockBase):
    type: Literal["audio"] = "audio"
    audio: dict[str, Any] = Field(default_factory=dict)


class EquationBlock(_BlockBase):
    type: Literal["equation"] = "equation"
    equation: dict[str, Any] = Field(default_factory=dict)


class SyncedBlock(_BlockBase):
    type: Literal["synced_block"] = "synced_block"
    synced_block: dict[str, Any] = Field(default_factory=dict)


class TemplateBlock(_BlockBase):
    type: Literal["template"] = "template"
    template: dict[str, Any] = Field(default_factory=dict)


class ChildPageBlock(_BlockBase):
    type: Literal["child_page"] = "child_page"
    child_page: dict[str, Any] = Field(default_factory=dict)


class ChildDatabaseBlock(_BlockBase):
    type: Literal["child_database"] = "child_database"
    child_database: dict[str, Any] = Field(default_factory=dict)


class LinkPreviewBlock(_BlockBase):
    type: Literal["link_preview"] = "link_preview"
    link_preview: dict[str, Any] = Field(default_factory=dict)


class UnsupportedBlock(_BlockBase):
    type: Literal["unsupported"] = "unsupported"
    unsupported: dict[str, Any] = Field(default_factory=dict)


class GenericBlock(_BlockBase):
    """Fallback variant for any block ``type`` the SDK does not yet model.

    The actual ``type`` string is preserved verbatim, and the type-specific
    data lives in ``__pydantic_extra__`` thanks to ``extra="allow"``.
    """

    type: str = ""


_KNOWN_BLOCK_TYPES = frozenset(
    {
        "paragraph",
        "heading_1",
        "heading_2",
        "heading_3",
        "bulleted_list_item",
        "numbered_list_item",
        "to_do",
        "toggle",
        "quote",
        "callout",
        "code",
        "divider",
        "breadcrumb",
        "table_of_contents",
        "column_list",
        "column",
        "link_to_page",
        "table",
        "table_row",
        "embed",
        "bookmark",
        "image",
        "video",
        "pdf",
        "file",
        "audio",
        "equation",
        "synced_block",
        "template",
        "child_page",
        "child_database",
        "link_preview",
        "unsupported",
    }
)


def _block_discriminator(value: Any) -> str:
    if isinstance(value, dict):
        tag = value.get("type")
    else:
        tag = getattr(value, "type", None)
    if isinstance(tag, str) and tag in _KNOWN_BLOCK_TYPES:
        return tag
    return "_generic"


Block = Annotated[
    Annotated[ParagraphBlock, Tag("paragraph")]
    | Annotated[Heading1Block, Tag("heading_1")]
    | Annotated[Heading2Block, Tag("heading_2")]
    | Annotated[Heading3Block, Tag("heading_3")]
    | Annotated[BulletedListItemBlock, Tag("bulleted_list_item")]
    | Annotated[NumberedListItemBlock, Tag("numbered_list_item")]
    | Annotated[ToDoBlock, Tag("to_do")]
    | Annotated[ToggleBlock, Tag("toggle")]
    | Annotated[QuoteBlock, Tag("quote")]
    | Annotated[CalloutBlock, Tag("callout")]
    | Annotated[CodeBlock, Tag("code")]
    | Annotated[DividerBlock, Tag("divider")]
    | Annotated[BreadcrumbBlock, Tag("breadcrumb")]
    | Annotated[TableOfContentsBlock, Tag("table_of_contents")]
    | Annotated[ColumnListBlock, Tag("column_list")]
    | Annotated[ColumnBlock, Tag("column")]
    | Annotated[LinkToPageBlock, Tag("link_to_page")]
    | Annotated[TableBlock, Tag("table")]
    | Annotated[TableRowBlock, Tag("table_row")]
    | Annotated[EmbedBlock, Tag("embed")]
    | Annotated[BookmarkBlock, Tag("bookmark")]
    | Annotated[ImageBlock, Tag("image")]
    | Annotated[VideoBlock, Tag("video")]
    | Annotated[PdfBlock, Tag("pdf")]
    | Annotated[FileBlock, Tag("file")]
    | Annotated[AudioBlock, Tag("audio")]
    | Annotated[EquationBlock, Tag("equation")]
    | Annotated[SyncedBlock, Tag("synced_block")]
    | Annotated[TemplateBlock, Tag("template")]
    | Annotated[ChildPageBlock, Tag("child_page")]
    | Annotated[ChildDatabaseBlock, Tag("child_database")]
    | Annotated[LinkPreviewBlock, Tag("link_preview")]
    | Annotated[UnsupportedBlock, Tag("unsupported")]
    | Annotated[GenericBlock, Tag("_generic")],
    Discriminator(_block_discriminator),
]


block_adapter: TypeAdapter[Any] = TypeAdapter(Block)
