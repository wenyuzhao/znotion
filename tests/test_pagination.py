"""Tests for znotion.pagination."""

from typing import Any

import pytest

from znotion.pagination import Page, paginate


def test_page_model_defaults() -> None:
    page: Page[int] = Page(results=[1, 2, 3])
    assert page.object == "list"
    assert page.results == [1, 2, 3]
    assert page.next_cursor is None
    assert page.has_more is False
    assert page.type is None


def test_page_model_full_payload() -> None:
    payload = {
        "object": "list",
        "results": [{"id": "a"}, {"id": "b"}],
        "next_cursor": "cur-1",
        "has_more": True,
        "type": "page",
    }
    page = Page[dict[str, Any]].model_validate(payload)
    assert page.results == [{"id": "a"}, {"id": "b"}]
    assert page.next_cursor == "cur-1"
    assert page.has_more is True
    assert page.type == "page"


class _Fetcher:
    def __init__(self, pages: list[Page[int]]) -> None:
        self._pages = pages
        self.calls: list[dict[str, Any]] = []

    async def __call__(self, **kwargs: Any) -> Page[int]:
        self.calls.append(kwargs)
        index = len(self.calls) - 1
        return self._pages[index]


async def test_paginate_three_pages_in_order() -> None:
    fetcher = _Fetcher(
        [
            Page[int](results=[1, 2], next_cursor="c1", has_more=True),
            Page[int](results=[3, 4], next_cursor="c2", has_more=True),
            Page[int](results=[5], next_cursor=None, has_more=False),
        ]
    )
    items = [item async for item in paginate(fetcher)]
    assert items == [1, 2, 3, 4, 5]
    assert len(fetcher.calls) == 3
    assert fetcher.calls[0]["start_cursor"] is None
    assert fetcher.calls[1]["start_cursor"] == "c1"
    assert fetcher.calls[2]["start_cursor"] == "c2"


async def test_paginate_forwards_page_size_and_kwargs() -> None:
    fetcher = _Fetcher(
        [
            Page[int](results=[10], next_cursor=None, has_more=False),
        ]
    )
    items = [
        item async for item in paginate(fetcher, page_size=50, database_id="db-123")
    ]
    assert items == [10]
    assert fetcher.calls == [
        {"start_cursor": None, "page_size": 50, "database_id": "db-123"},
    ]


async def test_paginate_omits_page_size_when_not_given() -> None:
    fetcher = _Fetcher(
        [
            Page[int](results=[1], next_cursor=None, has_more=False),
        ]
    )
    async for _ in paginate(fetcher):
        pass
    assert "page_size" not in fetcher.calls[0]


async def test_paginate_empty_first_page() -> None:
    fetcher = _Fetcher(
        [
            Page[int](results=[], next_cursor=None, has_more=False),
        ]
    )
    items = [item async for item in paginate(fetcher)]
    assert items == []
    assert len(fetcher.calls) == 1


async def test_paginate_stops_when_has_more_false_even_with_cursor() -> None:
    fetcher = _Fetcher(
        [
            Page[int](results=[1], next_cursor="leftover", has_more=False),
        ]
    )
    items = [item async for item in paginate(fetcher)]
    assert items == [1]
    assert len(fetcher.calls) == 1


async def test_paginate_stops_when_next_cursor_missing_despite_has_more() -> None:
    fetcher = _Fetcher(
        [
            Page[int](results=[1, 2], next_cursor=None, has_more=True),
        ]
    )
    items = [item async for item in paginate(fetcher)]
    assert items == [1, 2]
    assert len(fetcher.calls) == 1


async def test_paginate_typed_model_results() -> None:
    from znotion.models.common import SelectOption

    opt_a = SelectOption(id="a", name="A")
    opt_b = SelectOption(id="b", name="B")

    async def fetch(**_: Any) -> Page[SelectOption]:
        return Page[SelectOption](results=[opt_a, opt_b], has_more=False)

    items: list[SelectOption] = [item async for item in paginate(fetch)]
    assert items == [opt_a, opt_b]


@pytest.mark.parametrize("page_count", [1, 2, 5])
async def test_paginate_variable_page_counts(page_count: int) -> None:
    pages: list[Page[int]] = []
    for i in range(page_count):
        is_last = i == page_count - 1
        pages.append(
            Page[int](
                results=[i * 10, i * 10 + 1],
                next_cursor=None if is_last else f"c{i}",
                has_more=not is_last,
            )
        )
    fetcher = _Fetcher(pages)
    items = [item async for item in paginate(fetcher)]
    assert len(items) == page_count * 2
    assert len(fetcher.calls) == page_count
