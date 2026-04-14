"""Database object model."""

from typing import Literal

from pydantic import Field

from znotion.models.common import NotionModel, PartialUser
from znotion.models.files import Cover, Icon
from znotion.models.parent import Parent
from znotion.models.properties import PropertySchema
from znotion.models.rich_text import RichText


class DatabaseObject(NotionModel):
    """Notion database object returned by the Databases endpoints."""

    object: Literal["database"] = "database"
    id: str
    created_time: str
    last_edited_time: str
    created_by: PartialUser | None = None
    last_edited_by: PartialUser | None = None
    title: list[RichText] = Field(default_factory=list)
    description: list[RichText] = Field(default_factory=list)
    icon: Icon | None = None
    cover: Cover | None = None
    properties: dict[str, PropertySchema] = Field(default_factory=dict)
    parent: Parent
    url: str | None = None
    public_url: str | None = None
    archived: bool = False
    in_trash: bool = False
    is_inline: bool = False
