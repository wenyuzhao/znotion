"""Shared Notion object primitives used across resources."""

from typing import Literal

from pydantic import BaseModel, ConfigDict


class NotionModel(BaseModel):
    """Base class for all Notion API models.

    `extra="allow"` keeps unknown/future fields so the SDK doesn't break when
    Notion ships new fields. `populate_by_name=True` lets callers construct
    models using field names even if aliases are defined later.
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True)


Color = Literal[
    "default",
    "gray",
    "brown",
    "orange",
    "yellow",
    "green",
    "blue",
    "purple",
    "pink",
    "red",
    "gray_background",
    "brown_background",
    "orange_background",
    "yellow_background",
    "green_background",
    "blue_background",
    "purple_background",
    "pink_background",
    "red_background",
]


class Annotations(NotionModel):
    bold: bool = False
    italic: bool = False
    strikethrough: bool = False
    underline: bool = False
    code: bool = False
    color: str = "default"


class PartialUser(NotionModel):
    object: Literal["user"] = "user"
    id: str


class SelectOption(NotionModel):
    id: str | None = None
    name: str
    color: str | None = None
    description: str | None = None


class DateValue(NotionModel):
    start: str
    end: str | None = None
    time_zone: str | None = None


class EmojiObject(NotionModel):
    type: Literal["emoji"] = "emoji"
    emoji: str
