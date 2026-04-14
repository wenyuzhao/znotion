"""Typed exception hierarchy for Notion API errors."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import httpx


class NotionError(Exception):
    """Base class for all znotion errors raised by API calls."""

    def __init__(
        self,
        message: str,
        *,
        status: int | None = None,
        code: str | None = None,
        request_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status = status
        self.code = code
        self.request_id = request_id

    @classmethod
    def from_response(cls, response: httpx.Response) -> NotionError:
        status = response.status_code
        code: str | None = None
        message: str = ""
        request_id: str | None = None

        try:
            body = response.json()
        except ValueError:
            body = None

        if isinstance(body, dict):
            raw_code = body.get("code")
            raw_message = body.get("message")
            raw_request_id = body.get("request_id")
            if isinstance(raw_code, str):
                code = raw_code
            if isinstance(raw_message, str):
                message = raw_message
            if isinstance(raw_request_id, str):
                request_id = raw_request_id

        if not message:
            message = response.text or f"HTTP {status}"

        subclass = _select_subclass(status)
        return subclass(
            message,
            status=status,
            code=code,
            request_id=request_id,
        )


class NotionConfigError(NotionError):
    """Raised when required client-side configuration (e.g. NOTION_TOKEN) is missing."""


class NotionValidationError(NotionError):
    """Raised on HTTP 400 validation errors from the Notion API."""


class NotionAuthError(NotionError):
    """Raised on HTTP 401 unauthorized responses."""


class NotionForbiddenError(NotionError):
    """Raised on HTTP 403 forbidden responses."""


class NotionNotFoundError(NotionError):
    """Raised on HTTP 404 not-found responses."""


class NotionConflictError(NotionError):
    """Raised on HTTP 409 conflict responses."""


class NotionRateLimitError(NotionError):
    """Raised on HTTP 429 rate-limit responses."""


class NotionServerError(NotionError):
    """Raised on HTTP 5xx server errors."""


_STATUS_MAP: dict[int, type[NotionError]] = {
    400: NotionValidationError,
    401: NotionAuthError,
    403: NotionForbiddenError,
    404: NotionNotFoundError,
    409: NotionConflictError,
    429: NotionRateLimitError,
}


def _select_subclass(status: int) -> type[NotionError]:
    mapped = _STATUS_MAP.get(status)
    if mapped is not None:
        return mapped
    if 500 <= status < 600:
        return NotionServerError
    return NotionError
