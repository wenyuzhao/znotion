"""Property value and property schema models for pages and databases."""

from typing import Annotated, Any, Literal

from pydantic import Field

from znotion.models.common import (
    DateValue,
    NotionModel,
    PartialUser,
    SelectOption,
)
from znotion.models.files import FileObject
from znotion.models.rich_text import RichText


class _PropertyBase(NotionModel):
    id: str | None = None


# ---------------------------------------------------------------------------
# Property values (page.properties[name])
# ---------------------------------------------------------------------------


class TitlePropertyValue(_PropertyBase):
    type: Literal["title"] = "title"
    title: list[RichText] = Field(default_factory=list)


class RichTextPropertyValue(_PropertyBase):
    type: Literal["rich_text"] = "rich_text"
    rich_text: list[RichText] = Field(default_factory=list)


class NumberPropertyValue(_PropertyBase):
    type: Literal["number"] = "number"
    number: float | None = None


class SelectPropertyValue(_PropertyBase):
    type: Literal["select"] = "select"
    select: SelectOption | None = None


class MultiSelectPropertyValue(_PropertyBase):
    type: Literal["multi_select"] = "multi_select"
    multi_select: list[SelectOption] = Field(default_factory=list)


class StatusPropertyValue(_PropertyBase):
    type: Literal["status"] = "status"
    status: SelectOption | None = None


class DatePropertyValue(_PropertyBase):
    type: Literal["date"] = "date"
    date: DateValue | None = None


class FormulaPropertyValue(_PropertyBase):
    type: Literal["formula"] = "formula"
    formula: dict[str, Any]


class RelationItem(NotionModel):
    id: str


class RelationPropertyValue(_PropertyBase):
    type: Literal["relation"] = "relation"
    relation: list[RelationItem] = Field(default_factory=list)
    has_more: bool = False


class RollupPropertyValue(_PropertyBase):
    type: Literal["rollup"] = "rollup"
    rollup: dict[str, Any]


class PeoplePropertyValue(_PropertyBase):
    type: Literal["people"] = "people"
    people: list[PartialUser] = Field(default_factory=list)


class FilesPropertyValue(_PropertyBase):
    type: Literal["files"] = "files"
    files: list[FileObject] = Field(default_factory=list)


class CheckboxPropertyValue(_PropertyBase):
    type: Literal["checkbox"] = "checkbox"
    checkbox: bool = False


class UrlPropertyValue(_PropertyBase):
    type: Literal["url"] = "url"
    url: str | None = None


class EmailPropertyValue(_PropertyBase):
    type: Literal["email"] = "email"
    email: str | None = None


class PhoneNumberPropertyValue(_PropertyBase):
    type: Literal["phone_number"] = "phone_number"
    phone_number: str | None = None


class CreatedTimePropertyValue(_PropertyBase):
    type: Literal["created_time"] = "created_time"
    created_time: str


class CreatedByPropertyValue(_PropertyBase):
    type: Literal["created_by"] = "created_by"
    created_by: PartialUser


class LastEditedTimePropertyValue(_PropertyBase):
    type: Literal["last_edited_time"] = "last_edited_time"
    last_edited_time: str


class LastEditedByPropertyValue(_PropertyBase):
    type: Literal["last_edited_by"] = "last_edited_by"
    last_edited_by: PartialUser


class ButtonPropertyValue(_PropertyBase):
    type: Literal["button"] = "button"
    button: dict[str, Any] = Field(default_factory=dict)


class UniqueIdData(NotionModel):
    prefix: str | None = None
    number: int | None = None


class UniqueIdPropertyValue(_PropertyBase):
    type: Literal["unique_id"] = "unique_id"
    unique_id: UniqueIdData


class VerificationData(NotionModel):
    state: str
    verified_by: PartialUser | None = None
    date: DateValue | None = None


class VerificationPropertyValue(_PropertyBase):
    type: Literal["verification"] = "verification"
    verification: VerificationData | None = None


PropertyValue = Annotated[
    TitlePropertyValue
    | RichTextPropertyValue
    | NumberPropertyValue
    | SelectPropertyValue
    | MultiSelectPropertyValue
    | StatusPropertyValue
    | DatePropertyValue
    | FormulaPropertyValue
    | RelationPropertyValue
    | RollupPropertyValue
    | PeoplePropertyValue
    | FilesPropertyValue
    | CheckboxPropertyValue
    | UrlPropertyValue
    | EmailPropertyValue
    | PhoneNumberPropertyValue
    | CreatedTimePropertyValue
    | CreatedByPropertyValue
    | LastEditedTimePropertyValue
    | LastEditedByPropertyValue
    | ButtonPropertyValue
    | UniqueIdPropertyValue
    | VerificationPropertyValue,
    Field(discriminator="type"),
]


# ---------------------------------------------------------------------------
# Property schemas (database.properties[name])
# ---------------------------------------------------------------------------


class _PropertySchemaBase(NotionModel):
    id: str | None = None
    name: str | None = None
    description: str | None = None


class TitleSchema(_PropertySchemaBase):
    type: Literal["title"] = "title"
    title: dict[str, Any] = Field(default_factory=dict)


class RichTextSchema(_PropertySchemaBase):
    type: Literal["rich_text"] = "rich_text"
    rich_text: dict[str, Any] = Field(default_factory=dict)


class NumberSchemaConfig(NotionModel):
    format: str = "number"


class NumberSchema(_PropertySchemaBase):
    type: Literal["number"] = "number"
    number: NumberSchemaConfig = Field(default_factory=NumberSchemaConfig)


class SelectSchemaConfig(NotionModel):
    options: list[SelectOption] = Field(default_factory=list)


class SelectSchema(_PropertySchemaBase):
    type: Literal["select"] = "select"
    select: SelectSchemaConfig = Field(default_factory=SelectSchemaConfig)


class MultiSelectSchema(_PropertySchemaBase):
    type: Literal["multi_select"] = "multi_select"
    multi_select: SelectSchemaConfig = Field(default_factory=SelectSchemaConfig)


class StatusSchemaGroup(NotionModel):
    id: str | None = None
    name: str | None = None
    color: str | None = None
    option_ids: list[str] = Field(default_factory=list)


class StatusSchemaConfig(NotionModel):
    options: list[SelectOption] = Field(default_factory=list)
    groups: list[StatusSchemaGroup] = Field(default_factory=list)


class StatusSchema(_PropertySchemaBase):
    type: Literal["status"] = "status"
    status: StatusSchemaConfig = Field(default_factory=StatusSchemaConfig)


class DateSchema(_PropertySchemaBase):
    type: Literal["date"] = "date"
    date: dict[str, Any] = Field(default_factory=dict)


class PeopleSchema(_PropertySchemaBase):
    type: Literal["people"] = "people"
    people: dict[str, Any] = Field(default_factory=dict)


class FilesSchema(_PropertySchemaBase):
    type: Literal["files"] = "files"
    files: dict[str, Any] = Field(default_factory=dict)


class CheckboxSchema(_PropertySchemaBase):
    type: Literal["checkbox"] = "checkbox"
    checkbox: dict[str, Any] = Field(default_factory=dict)


class UrlSchema(_PropertySchemaBase):
    type: Literal["url"] = "url"
    url: dict[str, Any] = Field(default_factory=dict)


class EmailSchema(_PropertySchemaBase):
    type: Literal["email"] = "email"
    email: dict[str, Any] = Field(default_factory=dict)


class PhoneNumberSchema(_PropertySchemaBase):
    type: Literal["phone_number"] = "phone_number"
    phone_number: dict[str, Any] = Field(default_factory=dict)


class FormulaSchemaConfig(NotionModel):
    expression: str


class FormulaSchema(_PropertySchemaBase):
    type: Literal["formula"] = "formula"
    formula: FormulaSchemaConfig


class RelationSchemaConfig(NotionModel):
    database_id: str
    type: str | None = None
    single_property: dict[str, Any] | None = None
    dual_property: dict[str, Any] | None = None


class RelationSchema(_PropertySchemaBase):
    type: Literal["relation"] = "relation"
    relation: RelationSchemaConfig


class RollupSchemaConfig(NotionModel):
    relation_property_name: str | None = None
    relation_property_id: str | None = None
    rollup_property_name: str | None = None
    rollup_property_id: str | None = None
    function: str


class RollupSchema(_PropertySchemaBase):
    type: Literal["rollup"] = "rollup"
    rollup: RollupSchemaConfig


class CreatedTimeSchema(_PropertySchemaBase):
    type: Literal["created_time"] = "created_time"
    created_time: dict[str, Any] = Field(default_factory=dict)


class CreatedBySchema(_PropertySchemaBase):
    type: Literal["created_by"] = "created_by"
    created_by: dict[str, Any] = Field(default_factory=dict)


class LastEditedTimeSchema(_PropertySchemaBase):
    type: Literal["last_edited_time"] = "last_edited_time"
    last_edited_time: dict[str, Any] = Field(default_factory=dict)


class LastEditedBySchema(_PropertySchemaBase):
    type: Literal["last_edited_by"] = "last_edited_by"
    last_edited_by: dict[str, Any] = Field(default_factory=dict)


class ButtonSchema(_PropertySchemaBase):
    type: Literal["button"] = "button"
    button: dict[str, Any] = Field(default_factory=dict)


class UniqueIdSchemaConfig(NotionModel):
    prefix: str | None = None


class UniqueIdSchema(_PropertySchemaBase):
    type: Literal["unique_id"] = "unique_id"
    unique_id: UniqueIdSchemaConfig = Field(default_factory=UniqueIdSchemaConfig)


class VerificationSchema(_PropertySchemaBase):
    type: Literal["verification"] = "verification"
    verification: dict[str, Any] = Field(default_factory=dict)


PropertySchema = Annotated[
    TitleSchema
    | RichTextSchema
    | NumberSchema
    | SelectSchema
    | MultiSelectSchema
    | StatusSchema
    | DateSchema
    | PeopleSchema
    | FilesSchema
    | CheckboxSchema
    | UrlSchema
    | EmailSchema
    | PhoneNumberSchema
    | FormulaSchema
    | RelationSchema
    | RollupSchema
    | CreatedTimeSchema
    | CreatedBySchema
    | LastEditedTimeSchema
    | LastEditedBySchema
    | ButtonSchema
    | UniqueIdSchema
    | VerificationSchema,
    Field(discriminator="type"),
]
