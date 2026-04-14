"""File upload object model."""

from typing import Any, Literal

from znotion.models.common import NotionModel


class FileUpload(NotionModel):
    """Notion ``file_upload`` object returned by the File Uploads endpoints."""

    object: Literal["file_upload"] = "file_upload"
    id: str
    status: str
    filename: str | None = None
    content_type: str | None = None
    upload_url: str | None = None
    expiry_time: str | None = None
    number_of_parts: dict[str, Any] | None = None
