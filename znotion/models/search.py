"""Search result discriminated union.

Notion ``2025-09-03+`` returns pages and data sources from the search
endpoint — databases are no longer a possible result type.
"""

from typing import Annotated

from pydantic import Field, TypeAdapter

from znotion.models.data_sources import DataSourceObject
from znotion.models.pages import PageObject

SearchResult = Annotated[
    PageObject | DataSourceObject,
    Field(discriminator="object"),
]

search_result_adapter: TypeAdapter[PageObject | DataSourceObject] = TypeAdapter(
    SearchResult,
)
