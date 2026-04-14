"""Comment object model."""

from typing import Literal

from pydantic import Field

from znotion.models.common import NotionModel, PartialUser
from znotion.models.parent import Parent
from znotion.models.rich_text import RichText


class Comment(NotionModel):
    """Notion comment object returned by the Comments endpoints."""

    object: Literal["comment"] = "comment"
    id: str
    parent: Parent
    discussion_id: str
    created_time: str
    last_edited_time: str
    created_by: PartialUser | None = None
    rich_text: list[RichText] = Field(default_factory=list)
