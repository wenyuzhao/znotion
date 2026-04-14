"""Live integration tests for the File Uploads resource.

Skipped automatically when ``NOTION_TOKEN`` / ``NOTION_TEST_PAGE_ID`` are not
set. Mutations are confined to child pages archived via the ``created_pages``
fixture; uploaded files that are never attached to a page become orphaned on
the Notion side and expire naturally.

The multi-part test skips with a warning when the target workspace does not
permit multi-part uploads (e.g. Notion free-tier workspaces), so the suite
stays green on any plan while still exercising the full multi-part path when
the plan permits.
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from znotion import NotionClient
from znotion.errors import NotionValidationError
from znotion.models.blocks import FileBlock

pytestmark = [pytest.mark.live, pytest.mark.asyncio(loop_scope="session")]


# 1 KiB "PNG" — real PNG magic bytes followed by zero padding. Notion's upload
# endpoint accepts arbitrary bytes; the content_type label is what downstream
# consumers see.
_PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * (1024 - 8)

# Mirrors znotion.resources.file_uploads.SINGLE_PART_LIMIT (20 MiB). Duplicated
# here so the live test documents the exact byte threshold it's probing.
_SINGLE_PART_LIMIT = 20 * 1024 * 1024


def _title_property(text: str) -> dict[str, list[dict[str, dict[str, str]]]]:
    return {"title": [{"text": {"content": text}}]}


async def test_file_uploads_helper_and_low_level_single_part(
    notion: NotionClient,
    test_page_id: str,
    created_pages: list[str],
    tmp_path: Path,
) -> None:
    """Helper-based single-part upload + attach + low-level manual flow."""
    # --- high-level: upload_file helper + attach as file block -------------
    png_path = tmp_path / "tiny.png"
    png_path.write_bytes(_PNG_BYTES)

    upload = await notion.file_uploads.upload_file(
        png_path,
        content_type="image/png",
    )
    assert upload.status == "uploaded"
    assert upload.id

    parent = await notion.pages.create(
        parent={"type": "page_id", "page_id": test_page_id},
        properties={"title": _title_property("znotion live file uploads test")},
    )
    created_pages.append(parent.id)

    appended = await notion.blocks.append_children(
        parent.id,
        children=[
            {
                "type": "file",
                "file": {
                    "type": "file_upload",
                    "file_upload": {"id": upload.id},
                },
            },
        ],
    )
    assert len(appended.results) == 1
    block = appended.results[0]
    assert isinstance(block, FileBlock)
    assert block.id is not None

    refetched = await notion.blocks.retrieve(block.id)
    assert isinstance(refetched, FileBlock)
    file_data = refetched.model_dump(mode="json", exclude_none=True).get("file")
    assert isinstance(file_data, dict)
    assert "type" in file_data

    # --- low-level: manual create → send (single-part needs no complete) ---
    manual = await notion.file_uploads.create(
        mode="single_part",
        filename="manual.txt",
        content_type="text/plain",
    )
    assert manual.id
    assert manual.status == "pending"

    sent = await notion.file_uploads.send(
        manual.id,
        b"low-level manual upload",
        filename="manual.txt",
        content_type="text/plain",
    )
    assert sent.id == manual.id
    assert sent.status == "uploaded"

    retrieved = await notion.file_uploads.retrieve(manual.id)
    assert retrieved.status == "uploaded"


async def test_file_uploads_multi_part_low_level(
    notion: NotionClient,
    tmp_path: Path,
) -> None:
    """Manual ``create`` → ``send`` × N → ``complete`` for a >20 MiB file.

    Skipped with a warning when the target workspace forbids multi-part
    uploads (free tier). Uses a sparse file so the 20 MiB allocation is cheap
    on disk; total network upload is still ~20 MiB.
    """
    file_path = tmp_path / "big.txt"
    size = _SINGLE_PART_LIMIT + 1  # 20 MiB + 1 byte, just over the threshold
    part_size = (size // 2) + 1  # guarantees math.ceil(size / part_size) == 2
    with file_path.open("wb") as fh:
        fh.write(b"A" * size)

    num_parts = math.ceil(size / part_size)
    assert num_parts >= 2

    try:
        upload = await notion.file_uploads.create(
            mode="multi_part",
            filename="big.txt",
            content_type="text/plain",
            number_of_parts=num_parts,
        )
    except NotionValidationError as exc:
        message = str(exc).lower()
        if "multipart" in message or "multi_part" in message or "multi-part" in message:
            pytest.skip(f"workspace does not support multi-part uploads: {exc}")
        raise

    assert upload.id
    assert upload.status == "pending"

    with file_path.open("rb") as fh:
        for part_number in range(1, num_parts + 1):
            chunk = fh.read(part_size)
            assert chunk
            sent = await notion.file_uploads.send(
                upload.id,
                chunk,
                part_number=part_number,
                filename="big.txt",
                content_type="text/plain",
            )
            assert sent.id == upload.id

    completed = await notion.file_uploads.complete(upload.id)
    assert completed.status == "uploaded"
    assert completed.number_of_parts is not None
    total = completed.number_of_parts.get("total")
    assert total is not None
    assert int(total) >= 2

    retrieved = await notion.file_uploads.retrieve(upload.id)
    assert retrieved.id == upload.id
    assert retrieved.status == "uploaded"
