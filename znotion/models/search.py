"""Search result discriminated union."""

from typing import Annotated

from pydantic import Field, TypeAdapter

from znotion.models.databases import DatabaseObject
from znotion.models.pages import PageObject

SearchResult = Annotated[
    PageObject | DatabaseObject,
    Field(discriminator="object"),
]

search_result_adapter: TypeAdapter[PageObject | DatabaseObject] = TypeAdapter(SearchResult)
