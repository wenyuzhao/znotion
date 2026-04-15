"""Parent objects for Notion resources."""

from typing import Annotated, Literal

from pydantic import Field

from znotion.models.common import NotionModel


class DatabaseParent(NotionModel):
    type: Literal["database_id"] = "database_id"
    database_id: str


class DataSourceParent(NotionModel):
    type: Literal["data_source_id"] = "data_source_id"
    data_source_id: str


class PageParent(NotionModel):
    type: Literal["page_id"] = "page_id"
    page_id: str


class WorkspaceParent(NotionModel):
    type: Literal["workspace"] = "workspace"
    workspace: bool = True


class BlockParent(NotionModel):
    type: Literal["block_id"] = "block_id"
    block_id: str


Parent = Annotated[
    DatabaseParent | DataSourceParent | PageParent | WorkspaceParent | BlockParent,
    Field(discriminator="type"),
]
