"""NotionClient — top-level async client (implemented in later tasks)."""

from __future__ import annotations

from znotion.config import load_token


class NotionClient:
    """Async client for the Notion API.

    HTTP, retry, and resource surfaces are implemented in later tasks; this
    task only wires up token resolution so construction can be exercised.
    """

    def __init__(self, token: str | None = None) -> None:
        self._token: str = load_token(token)
