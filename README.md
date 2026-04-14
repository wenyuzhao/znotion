# znotion

An async Python SDK for the [Notion API](https://developers.notion.com/reference/intro), built on
`httpx` and `pydantic` v2.

- Async-first: every API call is an `async def`, resources share one `httpx.AsyncClient`.
- Typed models: Pydantic models for pages, databases, blocks, comments, search results, and file
  uploads. Unknown fields round-trip via `extra="allow"` so new Notion features don't break you.
- Auto-pagination: every list endpoint exposes both a single-page method (`*_page`) and an async
  iterator that walks every result.
- Typed errors: non-2xx responses raise a `NotionError` subclass (auth, not-found, rate-limit, …).

Requires Python 3.14+. Notion API version `2022-06-28`.

## Scope

In scope: Pages, Databases, Blocks, Comments, Search, File Uploads.

Out of scope (intentionally): the Users API and OAuth endpoints. Authenticate with a Notion
[internal integration token](https://developers.notion.com/docs/create-a-notion-integration).

## Install

```sh
uv add znotion
```

Only `uv` is supported — `pip` instructions are not provided. To work against a local checkout,
clone the repo and run `uv sync`; the package installs in editable mode automatically.

## Quickstart

Set `NOTION_TOKEN` in the environment or in a `.env` file in the working directory:

```sh
# .env
NOTION_TOKEN=ntn_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

Token resolution order: explicit `token=` argument → `./.env` → `os.environ["NOTION_TOKEN"]`. A
missing token raises `NotionConfigError`.

```python
import asyncio

from znotion import NotionClient


async def main() -> None:
    notion = NotionClient()
    page = await notion.pages.retrieve("PAGE_ID")
    print(page.id, page.url)


asyncio.run(main())
```

Pass `token="ntn_..."` explicitly to override environment/file lookup:

```python
notion = NotionClient(token="ntn_...")
```

### Reusing a pooled connection

Constructing `NotionClient` directly as above is the simplest way to use the library: each
request opens and closes its own short-lived `httpx.AsyncClient`, so there is nothing to clean
up. If you are making more than a handful of requests, use `async with` instead — it creates a
single pooled `httpx.AsyncClient` that is reused across every call, which is significantly
faster:

```python
async with NotionClient() as notion:
    page = await notion.pages.retrieve("PAGE_ID")
    async for row in notion.databases.query("DATABASE_ID"):
        print(row.id)
```

## Usage

All examples below assume a `notion = NotionClient()` bound at module or function scope (wrap
in `async with NotionClient() as notion:` if you want connection pooling).

### Create a page

```python
page = await notion.pages.create(
    parent={"database_id": "DATABASE_ID"},
    properties={
        "Name": {"title": [{"text": {"content": "Hello from znotion"}}]},
        "Status": {"select": {"name": "In progress"}},
    },
    children=[
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": "First paragraph."}}],
            },
        },
    ],
)
```

### Query a database (auto-pagination)

```python
async for row in notion.databases.query(
    "DATABASE_ID",
    filter={"property": "Status", "select": {"equals": "In progress"}},
    sorts=[{"timestamp": "created_time", "direction": "descending"}],
):
    print(row.id)
```

Use `query_page(...)` instead if you want manual cursor control:

```python
page = await notion.databases.query_page("DATABASE_ID", page_size=25)
for row in page.results:
    print(row.id)
if page.has_more:
    next_page = await notion.databases.query_page(
        "DATABASE_ID",
        page_size=25,
        start_cursor=page.next_cursor,
    )
```

### Append blocks

```python
await notion.blocks.append_children(
    "PAGE_OR_BLOCK_ID",
    children=[
        {
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": "Section"}}],
            },
        },
        {
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {
                "rich_text": [{"type": "text", "text": {"content": "One item"}}],
            },
        },
    ],
)

async for block in notion.blocks.children("PAGE_OR_BLOCK_ID"):
    print(block.type, block.id)
```

### Search

```python
async for result in notion.search.search(
    query="meeting notes",
    filter={"property": "object", "value": "page"},
):
    print(result.object, result.id)
```

### Create a comment

```python
await notion.comments.create(
    parent={"page_id": "PAGE_ID"},
    rich_text=[{"type": "text", "text": {"content": "Looks good!"}}],
)

async for comment in notion.comments.list(block_id="PAGE_OR_BLOCK_ID"):
    print(comment.id, comment.created_time)
```

Reply to an existing discussion by passing `discussion_id="..."` instead of `parent=`.

### Upload a file

```python
upload = await notion.file_uploads.upload_file("path/to/photo.jpg")

await notion.blocks.append_children(
    "PAGE_ID",
    children=[
        {
            "object": "block",
            "type": "image",
            "image": {
                "type": "file_upload",
                "file_upload": {"id": upload.id},
            },
        },
    ],
)
```

`upload_file` picks single-part or multi-part mode based on file size (Notion's single-part limit
is 20 MB). For manual control, use `file_uploads.create(...)`, `send(...)`, and `complete(...)`
directly.

## Error handling

Every non-2xx response raises a subclass of `NotionError`:

```python
from znotion import NotionClient, NotionNotFoundError, NotionRateLimitError

notion = NotionClient()
try:
    await notion.pages.retrieve("missing-id")
except NotionNotFoundError as exc:
    print("not found:", exc.message, exc.request_id)
except NotionRateLimitError:
    ...
```

The full set: `NotionValidationError` (400), `NotionAuthError` (401), `NotionForbiddenError`
(403), `NotionNotFoundError` (404), `NotionConflictError` (409), `NotionRateLimitError` (429),
`NotionServerError` (5xx), plus `NotionConfigError` for missing-token errors raised at
construction time.

## Contributor setup

```sh
uv sync                        # install deps (and znotion in editable mode)
uv run pytest                  # unit tests
uv run ruff check znotion tests
uv run pyright
```

Live integration tests hit the real Notion API and are skipped unless the required env vars are
set. Run them explicitly with:

```sh
uv run pytest -m live
```

See `tests/test_live_*.py` for the env vars each suite expects (at minimum `NOTION_TOKEN` plus a
scratch page or database id).
