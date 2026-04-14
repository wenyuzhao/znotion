"""Typed exception hierarchy for Notion API errors."""


class NotionError(Exception):
    """Base class for all znotion errors."""


class NotionConfigError(NotionError):
    """Raised when required configuration (e.g. NOTION_TOKEN) is missing or invalid."""
