"""Configuration loading (token + .env handling)."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import dotenv_values

from znotion.errors import NotionConfigError

_TOKEN_ENV_VAR = "NOTION_TOKEN"


def load_token(explicit: str | None = None) -> str:
    """Resolve the Notion API token.

    Resolution order:
    1. ``explicit`` argument if provided and non-empty.
    2. ``NOTION_TOKEN`` in a ``.env`` file in the current working directory.
    3. ``NOTION_TOKEN`` in the process environment.

    Raises :class:`NotionConfigError` if no token can be found.
    """
    if explicit:
        return explicit

    env_path = Path.cwd() / ".env"
    if env_path.is_file():
        values = dotenv_values(env_path)
        token = values.get(_TOKEN_ENV_VAR)
        if token:
            return token

    token = os.environ.get(_TOKEN_ENV_VAR)
    if token:
        return token

    raise NotionConfigError(
        f"{_TOKEN_ENV_VAR} not found. Set it in ./.env, export it in the environment, "
        "or pass token=... to NotionClient()."
    )
