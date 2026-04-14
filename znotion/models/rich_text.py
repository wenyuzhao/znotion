"""Rich text objects."""

from typing import Annotated, Any, Literal

from pydantic import Field

from znotion.models.common import Annotations, NotionModel


class LinkObject(NotionModel):
    url: str


class TextContent(NotionModel):
    content: str
    link: LinkObject | None = None


class EquationContent(NotionModel):
    expression: str


class RichTextText(NotionModel):
    type: Literal["text"] = "text"
    text: TextContent
    plain_text: str = ""
    href: str | None = None
    annotations: Annotations = Field(default_factory=Annotations)


class RichTextMention(NotionModel):
    type: Literal["mention"] = "mention"
    mention: dict[str, Any]
    plain_text: str = ""
    href: str | None = None
    annotations: Annotations = Field(default_factory=Annotations)


class RichTextEquation(NotionModel):
    type: Literal["equation"] = "equation"
    equation: EquationContent
    plain_text: str = ""
    href: str | None = None
    annotations: Annotations = Field(default_factory=Annotations)


RichText = Annotated[
    RichTextText | RichTextMention | RichTextEquation,
    Field(discriminator="type"),
]
