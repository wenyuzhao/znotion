"""File objects, icons, and covers."""

from typing import Annotated, Literal

from pydantic import Field

from znotion.models.common import EmojiObject, NotionModel
from znotion.models.rich_text import RichText


class InternalFileData(NotionModel):
    url: str
    expiry_time: str | None = None


class ExternalFileData(NotionModel):
    url: str


class FileUploadRefData(NotionModel):
    id: str


class InternalFile(NotionModel):
    type: Literal["file"] = "file"
    file: InternalFileData
    name: str | None = None
    caption: list[RichText] = Field(default_factory=list)


class ExternalFile(NotionModel):
    type: Literal["external"] = "external"
    external: ExternalFileData
    name: str | None = None
    caption: list[RichText] = Field(default_factory=list)


class FileUploadRef(NotionModel):
    type: Literal["file_upload"] = "file_upload"
    file_upload: FileUploadRefData
    name: str | None = None
    caption: list[RichText] = Field(default_factory=list)


FileObject = Annotated[
    InternalFile | ExternalFile | FileUploadRef,
    Field(discriminator="type"),
]

Icon = Annotated[
    EmojiObject | InternalFile | ExternalFile | FileUploadRef,
    Field(discriminator="type"),
]

Cover = Annotated[
    InternalFile | ExternalFile | FileUploadRef,
    Field(discriminator="type"),
]
