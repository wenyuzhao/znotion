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

    Injects the Notion auth header, API version, and JSON content type on
    every request, and raises :class:`NotionError` subclasses for non-2xx
    responses. No retry logic.
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
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers={
                "Authorization": f"Bearer {token}",
                "Notion-Version": notion_version,
                "Content-Type": "application/json",
            },
            timeout=timeout,
            transport=transport,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> Self:
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
        response = await self._client.request(method, path, json=json, params=params)
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
