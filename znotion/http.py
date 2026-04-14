"""Async HTTP transport for the Notion API."""

from __future__ import annotations

from types import TracebackType
from typing import Any, Self

import httpx

from znotion.errors import NotionError

DEFAULT_BASE_URL = "https://api.notion.com/v1"
DEFAULT_NOTION_VERSION = "2022-06-28"
DEFAULT_TIMEOUT = 30.0


class Transport:
    """Thin async wrapper around :class:`httpx.AsyncClient`.

    Injects the Notion auth header and API version on every request, and
    raises :class:`NotionError` subclasses for non-2xx responses. The
    ``Content-Type`` header is left to ``httpx`` to set per-request — its
    encoders pick ``application/json`` for ``json=`` bodies and the proper
    ``multipart/form-data; boundary=...`` for ``files=`` bodies. No retry
    logic.

    Two usage modes:

    * **Default** — used directly without ``async with``. ``_client`` stays
      ``None`` and each request opens (and closes) its own
      :class:`httpx.AsyncClient`. Slower per call, but lets callers do
      ``client = NotionClient(...)`` without committing to a context
      manager, and requires no cleanup.
    * **Pooled** — entered as an async context manager. A single
      :class:`httpx.AsyncClient` is created on ``__aenter__`` and reused
      across every request until ``__aexit__`` closes it. Preferred for any
      code that issues more than a couple of requests.
    """

    def __init__(
        self,
        token: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        notion_version: str = DEFAULT_NOTION_VERSION,
        timeout: float = DEFAULT_TIMEOUT,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._token = token
        self._base_url = base_url
        self._notion_version = notion_version
        self._timeout = timeout
        self._user_transport = transport
        self._client: httpx.AsyncClient | None = None

    def _new_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self._base_url,
            headers={
                "Authorization": f"Bearer {self._token}",
                "Notion-Version": self._notion_version,
            },
            timeout=self._timeout,
            transport=self._user_transport,
        )

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> Self:
        if self._client is None:
            self._client = self._new_client()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.close()

    async def request(
        self,
        method: str,
        path: str,
        *,
        json: Any = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if self._client is not None:
            response = await self._client.request(
                method, path, json=json, params=params
            )
        else:
            async with self._new_client() as client:
                response = await client.request(
                    method, path, json=json, params=params
                )
        if response.status_code >= 400:
            raise NotionError.from_response(response)
        data = response.json()
        if not isinstance(data, dict):
            raise NotionError(
                f"Expected JSON object from {method} {path}, got {type(data).__name__}",
                status=response.status_code,
            )
        return data

    async def get(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return await self.request("GET", path, params=params)

    async def post(
        self,
        path: str,
        *,
        json: Any = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return await self.request("POST", path, json=json, params=params)

    async def patch(
        self,
        path: str,
        *,
        json: Any = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return await self.request("PATCH", path, json=json, params=params)

    async def delete(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return await self.request("DELETE", path, params=params)

    async def post_multipart(
        self,
        path: str,
        *,
        files: dict[str, Any],
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """POST a ``multipart/form-data`` request and return the parsed JSON.

        Used by the File Uploads API to send file part bytes. ``files`` is
        passed through to ``httpx`` (which handles ``bytes``, file-like
        objects, and ``(filename, content, content_type)`` tuples) and
        ``data`` carries any extra form fields (e.g. ``part_number``).
        """
        if self._client is not None:
            response = await self._client.post(path, files=files, data=data)
        else:
            async with self._new_client() as client:
                response = await client.post(path, files=files, data=data)
        if response.status_code >= 400:
            raise NotionError.from_response(response)
        result = response.json()
        if not isinstance(result, dict):
            raise NotionError(
                f"Expected JSON object from POST {path}, got {type(result).__name__}",
                status=response.status_code,
            )
        return result
