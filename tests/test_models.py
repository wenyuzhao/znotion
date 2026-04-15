"""Round-trip tests for shared Notion object models."""

from typing import Any

import pytest
from pydantic import TypeAdapter

from znotion.models import (
    Annotations,
    BulletedListItemBlock,
    CodeBlock,
    DatabaseObject,
    DatabaseParent,
    EmojiObject,
    ExternalFile,
    FileObject,
    GenericBlock,
    Heading1Block,
    Icon,
    InternalFile,
    PageObject,
    ParagraphBlock,
    Parent,
    PropertySchema,
    PropertyValue,
    RichText,
    RichTextEquation,
    RichTextText,
    SelectOption,
    ToDoBlock,
    block_adapter,
)

PropertyValueAdapter: TypeAdapter[Any] = TypeAdapter(PropertyValue)
PropertySchemaAdapter: TypeAdapter[Any] = TypeAdapter(PropertySchema)
ParentAdapter: TypeAdapter[Any] = TypeAdapter(Parent)
FileObjectAdapter: TypeAdapter[Any] = TypeAdapter(FileObject)
IconAdapter: TypeAdapter[Any] = TypeAdapter(Icon)
RichTextAdapter: TypeAdapter[Any] = TypeAdapter(RichText)


def _roundtrip_adapter(adapter: TypeAdapter[Any], sample: dict[str, Any]) -> Any:
    parsed = adapter.validate_python(sample)
    dumped = adapter.dump_python(parsed, exclude_unset=True)
    reparsed = adapter.validate_python(dumped)
    assert reparsed == parsed
    return parsed


# ---------------------------------------------------------------------------
# Common primitives
# ---------------------------------------------------------------------------


def test_annotations_defaults():
    a = Annotations()
    assert a.bold is False
    assert a.color == "default"


def test_select_option_roundtrip():
    sample = {"id": "abc", "name": "Done", "color": "green"}
    opt = SelectOption.model_validate(sample)
    assert opt.name == "Done"
    assert opt.model_dump(exclude_unset=True) == sample


# ---------------------------------------------------------------------------
# Rich text discriminated union
# ---------------------------------------------------------------------------


def test_rich_text_text_roundtrip():
    sample = {
        "type": "text",
        "text": {"content": "Hello", "link": None},
        "plain_text": "Hello",
        "href": None,
        "annotations": {
            "bold": True,
            "italic": False,
            "strikethrough": False,
            "underline": False,
            "code": False,
            "color": "default",
        },
    }
    parsed = _roundtrip_adapter(RichTextAdapter, sample)
    assert isinstance(parsed, RichTextText)
    assert parsed.text.content == "Hello"
    assert parsed.annotations.bold is True


def test_rich_text_equation_roundtrip():
    sample = {
        "type": "equation",
        "equation": {"expression": "E = mc^2"},
        "plain_text": "E = mc^2",
        "href": None,
    }
    parsed = _roundtrip_adapter(RichTextAdapter, sample)
    assert isinstance(parsed, RichTextEquation)
    assert parsed.equation.expression == "E = mc^2"


def test_rich_text_mention_roundtrip():
    sample = {
        "type": "mention",
        "mention": {
            "type": "user",
            "user": {"object": "user", "id": "11111111-1111-1111-1111-111111111111"},
        },
        "plain_text": "@Alice",
        "href": None,
    }
    parsed = _roundtrip_adapter(RichTextAdapter, sample)
    assert parsed.plain_text == "@Alice"


# ---------------------------------------------------------------------------
# Parent discriminated union
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("sample", "expected_attr", "expected_value"),
    [
        (
            {"type": "database_id", "database_id": "db-123"},
            "database_id",
            "db-123",
        ),
        (
            {"type": "page_id", "page_id": "page-456"},
            "page_id",
            "page-456",
        ),
        (
            {"type": "block_id", "block_id": "block-789"},
            "block_id",
            "block-789",
        ),
        (
            {"type": "workspace", "workspace": True},
            "workspace",
            True,
        ),
    ],
)
def test_parent_variants_roundtrip(
    sample: dict[str, Any], expected_attr: str, expected_value: Any
) -> None:
    parsed = _roundtrip_adapter(ParentAdapter, sample)
    assert getattr(parsed, expected_attr) == expected_value


def test_parent_database_class_helper():
    p = DatabaseParent(database_id="db-1")
    assert p.type == "database_id"


# ---------------------------------------------------------------------------
# FileObject discriminated union
# ---------------------------------------------------------------------------


def test_file_object_internal_roundtrip():
    sample = {
        "type": "file",
        "file": {
            "url": "https://s3.amazonaws.com/...",
            "expiry_time": "2026-04-15T00:00:00.000Z",
        },
    }
    parsed = _roundtrip_adapter(FileObjectAdapter, sample)
    assert isinstance(parsed, InternalFile)
    assert parsed.file.url.startswith("https://")


def test_file_object_external_roundtrip():
    sample = {
        "type": "external",
        "external": {"url": "https://example.com/cat.png"},
        "name": "cat.png",
    }
    parsed = _roundtrip_adapter(FileObjectAdapter, sample)
    assert isinstance(parsed, ExternalFile)
    assert parsed.name == "cat.png"


def test_file_object_upload_ref_roundtrip():
    sample = {
        "type": "file_upload",
        "file_upload": {"id": "upload-abc"},
    }
    parsed = _roundtrip_adapter(FileObjectAdapter, sample)
    assert parsed.type == "file_upload"


def test_icon_emoji_roundtrip():
    sample = {"type": "emoji", "emoji": "🎉"}
    parsed = _roundtrip_adapter(IconAdapter, sample)
    assert isinstance(parsed, EmojiObject)
    assert parsed.emoji == "🎉"


def test_icon_external_file_roundtrip():
    sample = {
        "type": "external",
        "external": {"url": "https://example.com/icon.png"},
    }
    parsed = _roundtrip_adapter(IconAdapter, sample)
    assert isinstance(parsed, ExternalFile)


# ---------------------------------------------------------------------------
# Property values (discriminated union)
# ---------------------------------------------------------------------------


def test_property_value_title_roundtrip():
    sample = {
        "id": "title",
        "type": "title",
        "title": [
            {
                "type": "text",
                "text": {"content": "My Page", "link": None},
                "plain_text": "My Page",
                "href": None,
            }
        ],
    }
    parsed = _roundtrip_adapter(PropertyValueAdapter, sample)
    assert parsed.type == "title"
    assert parsed.title[0].text.content == "My Page"


def test_property_value_number_roundtrip():
    sample = {"id": "n", "type": "number", "number": 42.5}
    parsed = _roundtrip_adapter(PropertyValueAdapter, sample)
    assert parsed.number == 42.5


def test_property_value_select_roundtrip():
    sample = {
        "id": "sel",
        "type": "select",
        "select": {"id": "opt-1", "name": "Active", "color": "green"},
    }
    parsed = _roundtrip_adapter(PropertyValueAdapter, sample)
    assert parsed.select is not None
    assert parsed.select.name == "Active"


def test_property_value_multi_select_roundtrip():
    sample = {
        "id": "ms",
        "type": "multi_select",
        "multi_select": [
            {"id": "a", "name": "tag-a", "color": "blue"},
            {"id": "b", "name": "tag-b", "color": "red"},
        ],
    }
    parsed = _roundtrip_adapter(PropertyValueAdapter, sample)
    assert len(parsed.multi_select) == 2


def test_property_value_date_roundtrip():
    sample = {
        "id": "d",
        "type": "date",
        "date": {"start": "2026-04-14", "end": None, "time_zone": None},
    }
    parsed = _roundtrip_adapter(PropertyValueAdapter, sample)
    assert parsed.date is not None
    assert parsed.date.start == "2026-04-14"


def test_property_value_checkbox_roundtrip():
    sample = {"id": "c", "type": "checkbox", "checkbox": True}
    parsed = _roundtrip_adapter(PropertyValueAdapter, sample)
    assert parsed.checkbox is True


def test_property_value_url_roundtrip():
    sample = {"id": "u", "type": "url", "url": "https://example.com"}
    parsed = _roundtrip_adapter(PropertyValueAdapter, sample)
    assert parsed.url == "https://example.com"


def test_property_value_relation_roundtrip():
    sample = {
        "id": "r",
        "type": "relation",
        "relation": [{"id": "page-a"}, {"id": "page-b"}],
        "has_more": False,
    }
    parsed = _roundtrip_adapter(PropertyValueAdapter, sample)
    assert len(parsed.relation) == 2
    assert parsed.relation[0].id == "page-a"


def test_property_value_people_roundtrip():
    sample = {
        "id": "p",
        "type": "people",
        "people": [
            {"object": "user", "id": "user-1"},
            {"object": "user", "id": "user-2"},
        ],
    }
    parsed = _roundtrip_adapter(PropertyValueAdapter, sample)
    assert len(parsed.people) == 2


def test_property_value_unique_id_roundtrip():
    sample = {
        "id": "uid",
        "type": "unique_id",
        "unique_id": {"prefix": "TASK", "number": 17},
    }
    parsed = _roundtrip_adapter(PropertyValueAdapter, sample)
    assert parsed.unique_id.number == 17


def test_property_value_formula_roundtrip():
    sample = {
        "id": "f",
        "type": "formula",
        "formula": {"type": "string", "string": "computed"},
    }
    parsed = _roundtrip_adapter(PropertyValueAdapter, sample)
    assert parsed.formula["string"] == "computed"


def test_property_value_extra_field_preserved():
    sample = {
        "id": "n",
        "type": "number",
        "number": 1.0,
        "future_field": {"hello": "world"},
    }
    parsed = _roundtrip_adapter(PropertyValueAdapter, sample)
    dumped = PropertyValueAdapter.dump_python(parsed, exclude_unset=True)
    assert dumped["future_field"] == {"hello": "world"}


# ---------------------------------------------------------------------------
# Property schemas (discriminated union)
# ---------------------------------------------------------------------------


def test_property_schema_title_roundtrip():
    sample = {"id": "title", "name": "Name", "type": "title", "title": {}}
    parsed = _roundtrip_adapter(PropertySchemaAdapter, sample)
    assert parsed.name == "Name"


def test_property_schema_number_roundtrip():
    sample = {
        "id": "n",
        "name": "Score",
        "type": "number",
        "number": {"format": "percent"},
    }
    parsed = _roundtrip_adapter(PropertySchemaAdapter, sample)
    assert parsed.number.format == "percent"


def test_property_schema_select_roundtrip():
    sample = {
        "id": "s",
        "name": "Status",
        "type": "select",
        "select": {
            "options": [
                {"id": "a", "name": "open", "color": "red"},
                {"id": "b", "name": "done", "color": "green"},
            ]
        },
    }
    parsed = _roundtrip_adapter(PropertySchemaAdapter, sample)
    assert len(parsed.select.options) == 2


def test_property_schema_formula_roundtrip():
    sample = {
        "id": "f",
        "name": "Total",
        "type": "formula",
        "formula": {"expression": "prop(\"a\") + prop(\"b\")"},
    }
    parsed = _roundtrip_adapter(PropertySchemaAdapter, sample)
    assert parsed.formula.expression.startswith("prop")


def test_property_schema_relation_roundtrip():
    sample = {
        "id": "r",
        "name": "Linked",
        "type": "relation",
        "relation": {
            "database_id": "db-xyz",
            "type": "single_property",
            "single_property": {},
        },
    }
    parsed = _roundtrip_adapter(PropertySchemaAdapter, sample)
    assert parsed.relation.database_id == "db-xyz"


def test_property_schema_rollup_roundtrip():
    sample = {
        "id": "rl",
        "name": "Sum",
        "type": "rollup",
        "rollup": {
            "relation_property_name": "Linked",
            "relation_property_id": "abc",
            "rollup_property_name": "Score",
            "rollup_property_id": "def",
            "function": "sum",
        },
    }
    parsed = _roundtrip_adapter(PropertySchemaAdapter, sample)
    assert parsed.rollup.function == "sum"


def test_property_schema_extra_fields_preserved():
    sample = {
        "id": "x",
        "name": "X",
        "type": "checkbox",
        "checkbox": {},
        "future_thing": [1, 2, 3],
    }
    parsed = _roundtrip_adapter(PropertySchemaAdapter, sample)
    dumped = PropertySchemaAdapter.dump_python(parsed, exclude_unset=True)
    assert dumped["future_thing"] == [1, 2, 3]


# ---------------------------------------------------------------------------
# PageObject round-trip
# ---------------------------------------------------------------------------


def _page_sample() -> dict[str, Any]:
    return {
        "object": "page",
        "id": "11111111-1111-1111-1111-111111111111",
        "created_time": "2026-04-14T12:00:00.000Z",
        "last_edited_time": "2026-04-14T13:00:00.000Z",
        "created_by": {"object": "user", "id": "user-1"},
        "last_edited_by": {"object": "user", "id": "user-2"},
        "cover": {
            "type": "external",
            "external": {"url": "https://example.com/cover.png"},
        },
        "icon": {"type": "emoji", "emoji": "📝"},
        "parent": {"type": "data_source_id", "data_source_id": "ds-abc"},
        "is_archived": False,
        "in_trash": False,
        "url": "https://www.notion.so/Test-page-111",
        "public_url": None,
        "properties": {
            "Name": {
                "id": "title",
                "type": "title",
                "title": [
                    {
                        "type": "text",
                        "text": {"content": "Hello", "link": None},
                        "plain_text": "Hello",
                        "href": None,
                    }
                ],
            },
            "Score": {"id": "score", "type": "number", "number": 99.5},
            "Done": {"id": "done", "type": "checkbox", "checkbox": True},
        },
    }


def test_page_object_roundtrip():
    sample = _page_sample()
    parsed = PageObject.model_validate(sample)
    dumped = parsed.model_dump(exclude_unset=True, by_alias=True)
    reparsed = PageObject.model_validate(dumped)
    assert reparsed == parsed
    assert parsed.id == "11111111-1111-1111-1111-111111111111"
    assert parsed.parent.data_source_id == "ds-abc"
    assert parsed.icon is not None
    assert isinstance(parsed.icon, EmojiObject)
    assert parsed.properties["Name"].type == "title"
    assert parsed.properties["Score"].number == 99.5


def test_page_object_preserves_extra_fields():
    sample = _page_sample()
    sample["future_field"] = {"hello": "world"}
    parsed = PageObject.model_validate(sample)
    dumped = parsed.model_dump(exclude_unset=True)
    assert dumped["future_field"] == {"hello": "world"}


# ---------------------------------------------------------------------------
# DatabaseObject round-trip
# ---------------------------------------------------------------------------


def _database_sample() -> dict[str, Any]:
    return {
        "object": "database",
        "id": "22222222-2222-2222-2222-222222222222",
        "created_time": "2026-04-14T10:00:00.000Z",
        "last_edited_time": "2026-04-14T11:00:00.000Z",
        "created_by": {"object": "user", "id": "user-3"},
        "last_edited_by": {"object": "user", "id": "user-4"},
        "title": [
            {
                "type": "text",
                "text": {"content": "Tasks", "link": None},
                "plain_text": "Tasks",
                "href": None,
            }
        ],
        "description": [],
        "icon": None,
        "cover": None,
        "parent": {"type": "page_id", "page_id": "parent-page"},
        "url": "https://www.notion.so/Tasks-222",
        "public_url": None,
        "in_trash": False,
        "is_inline": False,
        "is_locked": False,
        "data_sources": [
            {"id": "ds-1", "name": "Tasks"},
        ],
    }


def test_database_object_roundtrip():
    sample = _database_sample()
    parsed = DatabaseObject.model_validate(sample)
    dumped = parsed.model_dump(exclude_unset=True, by_alias=True)
    reparsed = DatabaseObject.model_validate(dumped)
    assert reparsed == parsed
    assert parsed.id == "22222222-2222-2222-2222-222222222222"
    assert parsed.parent is not None
    assert parsed.parent.page_id == "parent-page"
    assert parsed.title[0].plain_text == "Tasks"
    assert parsed.data_sources[0].id == "ds-1"


def test_database_object_preserves_extra_fields():
    sample = _database_sample()
    sample["future_field"] = [1, 2, 3]
    parsed = DatabaseObject.model_validate(sample)
    dumped = parsed.model_dump(exclude_unset=True)
    assert dumped["future_field"] == [1, 2, 3]


# ---------------------------------------------------------------------------
# Block discriminated union
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("sample", "expected_cls"),
    [
        (
            {
                "object": "block",
                "id": "b-1",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {"content": "Hi", "link": None},
                            "plain_text": "Hi",
                            "href": None,
                        }
                    ],
                    "color": "default",
                },
                "has_children": False,
                "archived": False,
                "in_trash": False,
            },
            ParagraphBlock,
        ),
        (
            {
                "object": "block",
                "id": "b-2",
                "type": "heading_1",
                "heading_1": {"rich_text": [], "color": "default", "is_toggleable": False},
            },
            Heading1Block,
        ),
        (
            {
                "object": "block",
                "id": "b-3",
                "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": [], "color": "default"},
            },
            BulletedListItemBlock,
        ),
        (
            {
                "object": "block",
                "id": "b-4",
                "type": "to_do",
                "to_do": {"rich_text": [], "checked": True, "color": "default"},
            },
            ToDoBlock,
        ),
        (
            {
                "object": "block",
                "id": "b-5",
                "type": "code",
                "code": {
                    "rich_text": [],
                    "caption": [],
                    "language": "python",
                },
            },
            CodeBlock,
        ),
    ],
)
def test_block_variant_roundtrip(sample: dict[str, Any], expected_cls: type) -> None:
    parsed = block_adapter.validate_python(sample)
    assert isinstance(parsed, expected_cls)
    dumped = block_adapter.dump_python(parsed, exclude_unset=True)
    reparsed = block_adapter.validate_python(dumped)
    assert reparsed == parsed


def test_block_unknown_type_falls_back_to_generic():
    sample = {
        "object": "block",
        "id": "b-x",
        "type": "from_the_future",
        "from_the_future": {"foo": "bar"},
    }
    parsed = block_adapter.validate_python(sample)
    assert isinstance(parsed, GenericBlock)
    assert parsed.type == "from_the_future"
    dumped = block_adapter.dump_python(parsed, exclude_unset=True)
    assert dumped["from_the_future"] == {"foo": "bar"}


def test_block_extra_fields_preserved():
    sample = {
        "object": "block",
        "id": "b-7",
        "type": "paragraph",
        "paragraph": {"rich_text": [], "color": "default"},
        "future_envelope_field": "keep-me",
    }
    parsed = block_adapter.validate_python(sample)
    dumped = block_adapter.dump_python(parsed, exclude_unset=True)
    assert dumped["future_envelope_field"] == "keep-me"
