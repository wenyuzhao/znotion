# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

`znotion` is an async Python SDK for the Notion API (`2022-06-28`), built on `httpx` and `pydantic` v2. Requires Python 3.14+. Managed exclusively with `uv` — `pip` is not supported.

In-scope APIs: Pages, Databases, Blocks, Comments, Search, File Uploads. **Out of scope and must not be added**: the Users API and OAuth endpoints. Only internal-integration-token auth is supported.

## Commands

```sh
uv sync                            # install deps + znotion in editable mode
uv run pytest                      # unit tests (live tests auto-skip)
uv run pytest tests/test_foo.py    # one file
uv run pytest -k name              # one test by name
uv run pytest -m live              # live integration tests against real Notion API
uv run ruff check znotion tests
uv run pyright
```

Live tests need `NOTION_TOKEN` and `NOTION_TEST_PAGE_ID` (in `.env` or env). When either is missing, every `@pytest.mark.live` test is auto-skipped by [tests/conftest.py](tests/conftest.py).

## Architecture

Three layers, top to bottom:

1. **[NotionClient](znotion/client.py)** — owns one `Transport` and instantiates each resource class as an attribute (`pages`, `databases`, `blocks`, `comments`, `search`, `file_uploads`). The primary usage is direct construction (`notion = NotionClient()`); `async with NotionClient() as notion:` is the pooled-connection variant — see Transport below. Token resolution lives in [config.py](znotion/config.py): explicit arg → `./.env` → `os.environ["NOTION_TOKEN"]`, else `NotionConfigError`.

2. **[Transport](znotion/http.py)** — thin wrapper around `httpx.AsyncClient`. Injects `Authorization` and `Notion-Version` headers, raises `NotionError` subclasses for non-2xx responses (no retries). `Content-Type` is left to httpx so `json=` and `files=` bodies are encoded correctly. `post_multipart` is used by file uploads only.
   - **Default** (no `async with`): `_client` stays `None`; each request spins up a short-lived `httpx.AsyncClient` in an inner `async with` and closes it immediately. No `close()` required — this is what lets callers do `client = NotionClient(...)` without committing to a context manager.
   - **Pooled** (entered via `async with`): `__aenter__` creates a single `httpx.AsyncClient` and reuses it until `__aexit__` closes it. Preferred for any code that makes more than a couple of calls, since it avoids the per-request client setup cost.
   - When adding new request methods, check `self._client is not None` and fall back to `self._new_client()` like the existing ones.

3. **Resources** under [znotion/resources/](znotion/resources/) — one class per API surface. Every list endpoint exposes the pair:
   - `*_page(...)` → returns a `Page[T]` with `results / has_more / next_cursor` for manual cursor control.
   - bare method (e.g. `databases.query`, `blocks.children`, `comments.list`) → returns an `AsyncIterator[T]` that auto-paginates via [paginate()](znotion/pagination.py) (or an inline generator for `file_uploads.list`). When adding a new list endpoint, preserve this `*_page` + iterator pair.

### Models

[znotion/models/](znotion/models/) holds Pydantic v2 models for every resource. They all inherit `NotionModel` ([common.py](znotion/models/common.py)) which sets `extra="allow"` so unknown / future Notion fields round-trip without breaking the SDK — **do not** tighten this to `extra="forbid"`. Re-exports for the public API live in [znotion/__init__.py](znotion/__init__.py); add new public types there.

### Errors

[errors.py](znotion/errors.py) maps HTTP status to a `NotionError` subclass via `NotionError.from_response`: 400 → `NotionValidationError`, 401 → `NotionAuthError`, 403 → `NotionForbiddenError`, 404 → `NotionNotFoundError`, 409 → `NotionConflictError`, 429 → `NotionRateLimitError`, 5xx → `NotionServerError`. `NotionConfigError` is the only one not raised from an HTTP response.

### File uploads

[resources/file_uploads.py](znotion/resources/file_uploads.py) implements the three-step Notion flow (`create` → `send` → `complete`). `upload_file()` picks single-part vs multi-part using the 20 MB `SINGLE_PART_LIMIT`; multi-part chunks default to 10 MB. Notion rejects parts whose `Content-Type` doesn't match the value declared in `create`, so `send` always tags the multipart file part when `filename`/`content_type` are provided.

## Live test guardrails

[tests/conftest.py](tests/conftest.py) is the safety boundary for live tests:
- All mutations must be confined to descendants of the `test_page_id` fixture (the `NOTION_TEST_PAGE_ID` page).
- Use the `created_pages` / `created_databases` fixtures to register ids — they are archived in teardown via `pages.update(archived=True)` / `databases.update(archived=True)`.
- The conftest must never import or exercise any Users or workspace endpoint. Keep it that way.
