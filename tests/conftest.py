"""Shared pytest fixtures for znotion tests.

Exposes:
    * ``live`` marker — applied to tests that hit the real Notion API.
      Auto-skipped when ``NOTION_TOKEN`` or ``NOTION_TEST_PAGE_ID`` is absent
      from the environment / ``.env``.
    * ``notion`` (session) — shared live :class:`NotionClient`.
    * ``test_page_id`` (module) — root test page id under which every live
      test must confine its mutations.
    * ``created_pages`` (function) — collect page ids during a test; they are
      archived in teardown via ``pages.update(in_trash=True)``.
    * ``created_databases`` (function) — collect database ids during a test;
      they are archived in teardown via ``databases.update(in_trash=True)``.

Guardrail: the conftest never imports or exercises any users / workspace
endpoint. Only ``client.pages.update`` (archival of ids the test explicitly
registered) is invoked during teardown.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from dotenv import dotenv_values

from znotion import NotionClient, NotionError

_REPO_ROOT = Path(__file__).resolve().parent.parent
_ENV_PATH = _REPO_ROOT / ".env"
_TOKEN_KEY = "NOTION_TOKEN"
_PAGE_KEY = "NOTION_TEST_PAGE_ID"


def _load_env_var(key: str) -> str | None:
    """Read ``key`` from ``.env`` first, then from ``os.environ``."""
    if _ENV_PATH.is_file():
        value = dotenv_values(_ENV_PATH).get(key)
        if value:
            return value
    return os.environ.get(key) or None


_NOTION_TOKEN = _load_env_var(_TOKEN_KEY)
_NOTION_TEST_PAGE_ID = _load_env_var(_PAGE_KEY)
_LIVE_ENABLED = bool(_NOTION_TOKEN and _NOTION_TEST_PAGE_ID)


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "live: test hits the real Notion API; "
        "skipped when NOTION_TOKEN or NOTION_TEST_PAGE_ID is missing",
    )


def pytest_collection_modifyitems(
    config: pytest.Config,
    items: list[pytest.Item],
) -> None:
    if _LIVE_ENABLED:
        return
    missing = [
        name
        for name, value in ((_TOKEN_KEY, _NOTION_TOKEN), (_PAGE_KEY, _NOTION_TEST_PAGE_ID))
        if not value
    ]
    skip_marker = pytest.mark.skip(
        reason=f"live tests require {' and '.join(missing)}",
    )
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip_marker)


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def notion() -> AsyncIterator[NotionClient]:
    """Session-scoped live ``NotionClient``."""
    assert _NOTION_TOKEN, f"{_TOKEN_KEY} must be set before running live tests"
    assert _NOTION_TEST_PAGE_ID, f"{_PAGE_KEY} must be set before running live tests"
    async with NotionClient(token=_NOTION_TOKEN) as client:
        yield client


@pytest.fixture(scope="module")
def test_page_id() -> str:
    """Module-scoped root test page id.

    Every live test must confine all mutations to descendants of this page.
    """
    assert _NOTION_TEST_PAGE_ID, f"{_PAGE_KEY} must be set before running live tests"
    return _NOTION_TEST_PAGE_ID


@pytest_asyncio.fixture(loop_scope="session")
async def created_pages(notion: NotionClient) -> AsyncIterator[list[str]]:
    """Collect page ids during a test; archive them on teardown.

    Usage::

        async def test_foo(notion, test_page_id, created_pages):
            page = await notion.pages.create(...)
            created_pages.append(page.id)
    """
    ids: list[str] = []
    try:
        yield ids
    finally:
        for page_id in ids:
            try:
                await notion.pages.update(page_id, in_trash=True)
            except NotionError:
                # Teardown is best-effort: a failed archival should not mask
                # the test's own assertion failure.
                pass


@pytest_asyncio.fixture(loop_scope="session")
async def created_databases(notion: NotionClient) -> AsyncIterator[list[str]]:
    """Collect database ids during a test; archive them on teardown."""
    ids: list[str] = []
    try:
        yield ids
    finally:
        for database_id in ids:
            try:
                await notion.databases.update(database_id, in_trash=True)
            except NotionError:
                pass
