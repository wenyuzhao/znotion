"""NotionClient — top-level async client."""

from __future__ import annotations

from types import TracebackType
from typing import Self

import httpx

from znotion.config import load_token
from znotion.http import (
    DEFAULT_BASE_URL,
    DEFAULT_NOTION_VERSION,
    DEFAULT_TIMEOUT,
    Transport,
)
from znotion.resources.blocks import BlocksResource
from znotion.resources.comments import CommentsResource
from znotion.resources.databases import DatabasesResource
from znotion.resources.pages import PagesResource
from znotion.resources.search import SearchResource


class NotionClient:
    """Async client for the Notion API.

    Resource surfaces (``pages``, ``databases``, ``blocks``, ``comments``,
    ``search``, ``file_uploads``) are exposed as attributes on the client.
    """

    def __init__(
        self,
        token: str | None = None,
        *,
        base_url: str = DEFAULT_BASE_URL,
        notion_version: str = DEFAULT_NOTION_VERSION,
        timeout: float = DEFAULT_TIMEOUT,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._token: str = load_token(token)
        self._transport = Transport(
            self._token,
            base_url=base_url,
            notion_version=notion_version,
            timeout=timeout,
            transport=transport,
        )
        self.pages = PagesResource(self._transport)
        self.databases = DatabasesResource(self._transport)
        self.blocks = BlocksResource(self._transport)
        self.comments = CommentsResource(self._transport)
        self.search = SearchResource(self._transport)

    async def close(self) -> None:
        await self._transport.close()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.close()
