"""Data source object model (Notion API 2025-09-03+).

Data sources replaced the inline database schema: a database now contains a
list of data sources, each with its own property schema. Queries and schema
operations all live on the data source, not the database.
"""

from typing import Literal

from pydantic import Field

from znotion.models.common import NotionModel, PartialUser
from znotion.models.files import Cover, Icon
from znotion.models.parent import Parent
from znotion.models.properties import PropertySchema
from znotion.models.rich_text import RichText


class DataSourceObject(NotionModel):
    """Notion data source object returned by the Data Sources endpoints."""

    object: Literal["data_source"] = "data_source"
    id: str
    created_time: str | None = None
    last_edited_time: str | None = None
    created_by: PartialUser | None = None
    last_edited_by: PartialUser | None = None
    title: list[RichText] = Field(default_factory=list)
    description: list[RichText] = Field(default_factory=list)
    icon: Icon | None = None
    cover: Cover | None = None
    properties: dict[str, PropertySchema] = Field(default_factory=dict)
    parent: Parent | None = None
    database_parent: Parent | None = None
    url: str | None = None
    public_url: str | None = None
    in_trash: bool = False
    is_inline: bool = False
