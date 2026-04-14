"""Unit tests for znotion.resources.file_uploads.FileUploadsResource."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx

from znotion import FileUpload, FileUploadsResource, NotionClient, Page


def _file_upload_payload(
    *,
    upload_id: str = "fu_1",
    status: str = "pending",
    filename: str = "report.pdf",
    content_type: str = "application/pdf",
    upload_url: str | None = "https://api.notion.com/v1/file_uploads/fu_1/send",
    number_of_parts: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "object": "file_upload",
        "id": upload_id,
        "status": status,
        "filename": filename,
        "content_type": content_type,
        "upload_url": upload_url,
        "expiry_time": "2099-01-01T00:00:00.000Z",
    }
    if number_of_parts is not None:
        payload["number_of_parts"] = number_of_parts
    return payload


def _list_payload(items: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
    return {
        "object": "list",
        "results": items,
        "next_cursor": kwargs.get("next_cursor"),
        "has_more": kwargs.get("has_more", False),
        "type": "file_upload",
    }


def _make_client(handler: Any) -> NotionClient:
    return NotionClient(token="secret_test", transport=httpx.MockTransport(handler))


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------


async def test_create_single_part_posts_minimal_body() -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["path"] = request.url.path
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json=_file_upload_payload())

    async with _make_client(handler) as client:
        result = await client.file_uploads.create(
            mode="single_part",
            filename="report.pdf",
            content_type="application/pdf",
        )

    assert seen["method"] == "POST"
    assert seen["path"] == "/v1/file_uploads"
    assert seen["body"] == {
        "mode": "single_part",
        "filename": "report.pdf",
        "content_type": "application/pdf",
    }
    assert isinstance(result, FileUpload)
    assert result.id == "fu_1"
    assert result.status == "pending"
    assert result.filename == "report.pdf"
    assert result.content_type == "application/pdf"
    assert result.upload_url == "https://api.notion.com/v1/file_uploads/fu_1/send"


async def test_create_multi_part_includes_number_of_parts() -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json=_file_upload_payload(
                status="pending",
                number_of_parts={"total": 3, "sent": 0},
            ),
        )

    async with _make_client(handler) as client:
        result = await client.file_uploads.create(
            mode="multi_part",
            filename="big.bin",
            content_type="application/octet-stream",
            number_of_parts=3,
        )

    assert seen["body"] == {
        "mode": "multi_part",
        "filename": "big.bin",
        "content_type": "application/octet-stream",
        "number_of_parts": 3,
    }
    assert result.number_of_parts == {"total": 3, "sent": 0}


async def test_create_external_url_includes_external_url() -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json=_file_upload_payload(status="uploaded"))

    async with _make_client(handler) as client:
        await client.file_uploads.create(
            mode="external_url",
            external_url="https://example.test/file.png",
            filename="file.png",
            content_type="image/png",
        )

    assert seen["body"] == {
        "mode": "external_url",
        "filename": "file.png",
        "content_type": "image/png",
        "external_url": "https://example.test/file.png",
    }


async def test_create_omits_unspecified_kwargs() -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json=_file_upload_payload())

    async with _make_client(handler) as client:
        await client.file_uploads.create()

    assert seen["body"] == {"mode": "single_part"}


# ---------------------------------------------------------------------------
# send
# ---------------------------------------------------------------------------


async def test_send_uploads_bytes_via_multipart() -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["path"] = request.url.path
        seen["content_type"] = request.headers.get("content-type")
        seen["body"] = request.content
        return httpx.Response(200, json=_file_upload_payload(status="uploaded"))

    async with _make_client(handler) as client:
        result = await client.file_uploads.send("fu_1", b"hello world")

    assert seen["method"] == "POST"
    assert seen["path"] == "/v1/file_uploads/fu_1/send"
    content_type = seen["content_type"]
    assert isinstance(content_type, str)
    assert content_type.startswith("multipart/form-data; boundary=")
    body = seen["body"]
    assert isinstance(body, bytes)
    assert b"hello world" in body
    assert b'name="file"' in body
    assert b'name="part_number"' not in body
    assert isinstance(result, FileUpload)
    assert result.status == "uploaded"


async def test_send_with_part_number_includes_form_field() -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = request.content
        return httpx.Response(200, json=_file_upload_payload())

    async with _make_client(handler) as client:
        await client.file_uploads.send("fu_1", b"chunk-2", part_number=2)

    body = seen["body"]
    assert isinstance(body, bytes)
    assert b'name="part_number"' in body
    assert b"\r\n\r\n2\r\n" in body
    assert b"chunk-2" in body


async def test_send_accepts_binary_io() -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = request.content
        return httpx.Response(200, json=_file_upload_payload())

    import io

    async with _make_client(handler) as client:
        await client.file_uploads.send("fu_1", io.BytesIO(b"stream-data"))

    body = seen["body"]
    assert isinstance(body, bytes)
    assert b"stream-data" in body


# ---------------------------------------------------------------------------
# complete / retrieve
# ---------------------------------------------------------------------------


async def test_complete_posts_to_complete_endpoint() -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["path"] = request.url.path
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json=_file_upload_payload(status="uploaded"))

    async with _make_client(handler) as client:
        result = await client.file_uploads.complete("fu_1")

    assert seen["method"] == "POST"
    assert seen["path"] == "/v1/file_uploads/fu_1/complete"
    assert seen["body"] == {}
    assert result.status == "uploaded"


async def test_retrieve_gets_by_id() -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["path"] = request.url.path
        return httpx.Response(200, json=_file_upload_payload())

    async with _make_client(handler) as client:
        result = await client.file_uploads.retrieve("fu_1")

    assert seen["method"] == "GET"
    assert seen["path"] == "/v1/file_uploads/fu_1"
    assert result.id == "fu_1"


# ---------------------------------------------------------------------------
# list_page / list
# ---------------------------------------------------------------------------


async def test_list_page_forwards_query_params() -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["params"] = dict(request.url.params)
        return httpx.Response(
            200,
            json=_list_payload([_file_upload_payload(upload_id="fu_a")]),
        )

    async with _make_client(handler) as client:
        page = await client.file_uploads.list_page(
            status="pending",
            page_size=5,
            start_cursor="cur-1",
        )

    assert seen["path"] == "/v1/file_uploads"
    assert seen["params"] == {
        "status": "pending",
        "page_size": "5",
        "start_cursor": "cur-1",
    }
    assert isinstance(page, Page)
    assert len(page.results) == 1
    assert page.results[0].id == "fu_a"


async def test_list_page_omits_unset_params() -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["params"] = dict(request.url.params)
        return httpx.Response(200, json=_list_payload([]))

    async with _make_client(handler) as client:
        await client.file_uploads.list_page()

    assert seen["params"] == {}


async def test_list_auto_paginates_two_pages() -> None:
    calls: list[dict[str, Any]] = []
    pages = [
        _list_payload(
            [_file_upload_payload(upload_id="fu_1")],
            has_more=True,
            next_cursor="cur-2",
        ),
        _list_payload([_file_upload_payload(upload_id="fu_2")]),
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(dict(request.url.params))
        return httpx.Response(200, json=pages[len(calls) - 1])

    async with _make_client(handler) as client:
        ids = [item.id async for item in client.file_uploads.list(status="uploaded", page_size=2)]

    assert ids == ["fu_1", "fu_2"]
    assert calls == [
        {"status": "uploaded", "page_size": "2"},
        {"status": "uploaded", "page_size": "2", "start_cursor": "cur-2"},
    ]


async def test_list_stops_on_missing_next_cursor() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=_list_payload(
                [_file_upload_payload(upload_id="fu_only")],
                has_more=True,
                next_cursor=None,
            ),
        )

    async with _make_client(handler) as client:
        ids = [item.id async for item in client.file_uploads.list()]

    assert ids == ["fu_only"]


async def test_list_stops_on_has_more_false_with_stale_cursor() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=_list_payload(
                [_file_upload_payload(upload_id="fu_only")],
                has_more=False,
                next_cursor="leftover",
            ),
        )

    async with _make_client(handler) as client:
        ids = [item.id async for item in client.file_uploads.list()]

    assert ids == ["fu_only"]


# ---------------------------------------------------------------------------
# upload_file helper
# ---------------------------------------------------------------------------


async def test_upload_file_single_part_for_small_file(tmp_path: Path) -> None:
    file_path = tmp_path / "small.txt"
    file_path.write_bytes(b"tiny content")

    calls: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        entry: dict[str, Any] = {
            "method": request.method,
            "path": request.url.path,
            "content_type": request.headers.get("content-type"),
            "raw": request.content,
        }
        if entry["content_type"] == "application/json":
            entry["body"] = json.loads(request.content)
        calls.append(entry)
        if request.url.path == "/v1/file_uploads":
            return httpx.Response(200, json=_file_upload_payload(upload_id="fu_small"))
        return httpx.Response(
            200,
            json=_file_upload_payload(upload_id="fu_small", status="uploaded"),
        )

    async with _make_client(handler) as client:
        result = await client.file_uploads.upload_file(file_path)

    assert len(calls) == 2
    assert calls[0]["path"] == "/v1/file_uploads"
    assert calls[0]["body"] == {
        "mode": "single_part",
        "filename": "small.txt",
        "content_type": "text/plain",
    }
    assert calls[1]["path"] == "/v1/file_uploads/fu_small/send"
    send_ct = calls[1]["content_type"]
    assert isinstance(send_ct, str)
    assert send_ct.startswith("multipart/form-data; boundary=")
    raw = calls[1]["raw"]
    assert isinstance(raw, bytes)
    assert b"tiny content" in raw
    assert b'name="part_number"' not in raw
    assert result.id == "fu_small"
    assert result.status == "uploaded"


async def test_upload_file_multi_part_for_large_file(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    from znotion.resources import file_uploads as fu_module

    monkeypatch.setattr(fu_module, "SINGLE_PART_LIMIT", 20)

    file_path = tmp_path / "big.bin"
    payload = b"A" * 25
    file_path.write_bytes(payload)

    calls: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        entry: dict[str, Any] = {
            "method": request.method,
            "path": request.url.path,
            "content_type": request.headers.get("content-type"),
            "raw": request.content,
        }
        if entry["content_type"] == "application/json":
            entry["body"] = json.loads(request.content)
        calls.append(entry)
        return httpx.Response(200, json=_file_upload_payload(upload_id="fu_big", status="uploaded"))

    async with _make_client(handler) as client:
        result = await client.file_uploads.upload_file(
            file_path,
            content_type="application/octet-stream",
            part_size=10,
        )

    paths = [c["path"] for c in calls]
    assert paths == [
        "/v1/file_uploads",
        "/v1/file_uploads/fu_big/send",
        "/v1/file_uploads/fu_big/send",
        "/v1/file_uploads/fu_big/send",
        "/v1/file_uploads/fu_big/complete",
    ]

    assert calls[0]["body"] == {
        "mode": "multi_part",
        "filename": "big.bin",
        "content_type": "application/octet-stream",
        "number_of_parts": 3,
    }

    sent_chunks: list[bytes] = []
    sent_part_numbers: list[bytes] = []
    for entry in calls[1:4]:
        raw = entry["raw"]
        assert isinstance(raw, bytes)
        assert b'name="part_number"' in raw
        # Extract the part number value
        marker = b'name="part_number"\r\n\r\n'
        idx = raw.find(marker)
        assert idx >= 0
        end = raw.find(b"\r\n", idx + len(marker))
        sent_part_numbers.append(raw[idx + len(marker) : end])
        sent_chunks.append(raw)

    assert sent_part_numbers == [b"1", b"2", b"3"]
    # All the file bytes should appear across the three sends.
    combined = b"".join(sent_chunks)
    assert combined.count(b"A") == 25

    assert calls[4]["body"] == {}
    assert result.id == "fu_big"
    assert result.status == "uploaded"


async def test_upload_file_uses_filename_override(tmp_path: Path) -> None:
    file_path = tmp_path / "data.bin"
    file_path.write_bytes(b"x" * 8)

    seen_body: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/file_uploads":
            seen_body.update(json.loads(request.content))
        return httpx.Response(200, json=_file_upload_payload(upload_id="fu_x", status="uploaded"))

    async with _make_client(handler) as client:
        await client.file_uploads.upload_file(
            file_path,
            filename="renamed.bin",
            content_type="application/x-custom",
        )

    assert seen_body == {
        "mode": "single_part",
        "filename": "renamed.bin",
        "content_type": "application/x-custom",
    }


# ---------------------------------------------------------------------------
# wiring
# ---------------------------------------------------------------------------


async def test_client_exposes_file_uploads_resource() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_file_upload_payload())

    async with _make_client(handler) as client:
        assert isinstance(client.file_uploads, FileUploadsResource)
