"""File uploads resource — wraps the ``/v1/file_uploads`` endpoints."""

from __future__ import annotations

import math
import mimetypes
from collections.abc import AsyncIterator
from pathlib import Path
from typing import IO, Any

from znotion.http import Transport
from znotion.models.file_uploads import FileUpload
from znotion.pagination import Page

SINGLE_PART_LIMIT = 20 * 1024 * 1024
DEFAULT_PART_SIZE = 10 * 1024 * 1024


class FileUploadsResource:
    """Methods for the Notion File Uploads API.

    Exposed on the client as ``client.file_uploads``.
    """

    def __init__(self, transport: Transport) -> None:
        self._transport = transport

    async def create(
        self,
        *,
        mode: str = "single_part",
        filename: str | None = None,
        content_type: str | None = None,
        number_of_parts: int | None = None,
        external_url: str | None = None,
    ) -> FileUpload:
        """Create a ``file_upload`` object.

        ``mode`` selects the upload strategy: ``"single_part"`` (one
        ``send`` call), ``"multi_part"`` (requires ``number_of_parts`` and
        a final ``complete`` call), or ``"external_url"`` (Notion fetches
        from ``external_url`` server-side — no ``send`` needed).
        """
        body: dict[str, Any] = {"mode": mode}
        if filename is not None:
            body["filename"] = filename
        if content_type is not None:
            body["content_type"] = content_type
        if number_of_parts is not None:
            body["number_of_parts"] = number_of_parts
        if external_url is not None:
            body["external_url"] = external_url
        data = await self._transport.post("/file_uploads", json=body)
        return FileUpload.model_validate(data)

    async def send(
        self,
        file_upload_id: str,
        file: bytes | IO[bytes],
        *,
        part_number: int | None = None,
        filename: str | None = None,
        content_type: str | None = None,
    ) -> FileUpload:
        """Upload bytes for a ``file_upload``.

        For ``single_part`` uploads call once with the whole payload. For
        ``multi_part`` uploads call once per part and pass ``part_number``
        (1-indexed). Pass ``content_type`` (and optionally ``filename``) to
        tag the multipart file part — Notion rejects the request when the
        part's content-type does not match the value declared in ``create``.
        When neither is provided, httpx defaults the part to
        ``application/octet-stream``.
        """
        files: dict[str, Any]
        if filename is not None or content_type is not None:
            files = {
                "file": (
                    filename or "file",
                    file,
                    content_type or "application/octet-stream",
                ),
            }
        else:
            files = {"file": file}
        form: dict[str, Any] = {}
        if part_number is not None:
            form["part_number"] = str(part_number)
        data = await self._transport.post_multipart(
            f"/file_uploads/{file_upload_id}/send",
            files=files,
            data=form or None,
        )
        return FileUpload.model_validate(data)

    async def complete(self, file_upload_id: str) -> FileUpload:
        """Mark a ``multi_part`` file upload as complete."""
        data = await self._transport.post(
            f"/file_uploads/{file_upload_id}/complete",
            json={},
        )
        return FileUpload.model_validate(data)

    async def retrieve(self, file_upload_id: str) -> FileUpload:
        """Retrieve a ``file_upload`` object by id."""
        data = await self._transport.get(f"/file_uploads/{file_upload_id}")
        return FileUpload.model_validate(data)

    async def list_page(
        self,
        *,
        status: str | None = None,
        page_size: int | None = None,
        start_cursor: str | None = None,
    ) -> Page[FileUpload]:
        """Fetch a single page of ``file_upload`` objects."""
        params: dict[str, Any] = {}
        if status is not None:
            params["status"] = status
        if page_size is not None:
            params["page_size"] = page_size
        if start_cursor is not None:
            params["start_cursor"] = start_cursor
        data = await self._transport.get("/file_uploads", params=params or None)
        return Page[FileUpload].model_validate(data)

    def list(
        self,
        *,
        status: str | None = None,
        page_size: int | None = None,
    ) -> AsyncIterator[FileUpload]:
        """List ``file_upload`` objects, auto-paginating the results."""

        async def gen() -> AsyncIterator[FileUpload]:
            cursor: str | None = None
            while True:
                page = await self.list_page(
                    status=status,
                    page_size=page_size,
                    start_cursor=cursor,
                )
                for item in page.results:
                    yield item
                if not page.has_more or page.next_cursor is None:
                    return
                cursor = page.next_cursor

        return gen()

    async def upload_file(
        self,
        path: str | Path,
        *,
        filename: str | None = None,
        content_type: str | None = None,
        part_size: int = DEFAULT_PART_SIZE,
    ) -> FileUpload:
        """Upload a local file, choosing single- vs multi-part automatically.

        Files at or below Notion's 20 MB single-part limit go through one
        ``create(mode="single_part")`` + one ``send`` call. Larger files
        are split into ``part_size``-byte chunks (default 10 MB), uploaded
        through ``create(mode="multi_part", number_of_parts=...)`` + one
        ``send(part_number=i)`` per chunk, and finalized with ``complete``.
        """
        file_path = Path(path)
        size = file_path.stat().st_size
        resolved_filename = filename or file_path.name
        guessed, _ = mimetypes.guess_type(str(file_path))
        resolved_content_type = content_type or guessed or "application/octet-stream"

        if size <= SINGLE_PART_LIMIT:
            upload = await self.create(
                mode="single_part",
                filename=resolved_filename,
                content_type=resolved_content_type,
            )
            with file_path.open("rb") as fh:
                payload = fh.read()
            return await self.send(
                upload.id,
                payload,
                filename=resolved_filename,
                content_type=resolved_content_type,
            )

        num_parts = max(1, math.ceil(size / part_size))
        upload = await self.create(
            mode="multi_part",
            filename=resolved_filename,
            content_type=resolved_content_type,
            number_of_parts=num_parts,
        )
        with file_path.open("rb") as fh:
            for part_number in range(1, num_parts + 1):
                chunk = fh.read(part_size)
                if not chunk:
                    break
                await self.send(
                    upload.id,
                    chunk,
                    part_number=part_number,
                    filename=resolved_filename,
                    content_type=resolved_content_type,
                )
        return await self.complete(upload.id)
