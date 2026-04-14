"""Tests for znotion.config.load_token."""

from __future__ import annotations

from pathlib import Path

import pytest

from znotion import NotionClient, NotionConfigError
from znotion.config import load_token


def _write_env(path: Path, token: str) -> None:
    (path / ".env").write_text(f"NOTION_TOKEN={token}\n")


def test_explicit_token_wins(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    _write_env(tmp_path, "from_dotenv")
    monkeypatch.setenv("NOTION_TOKEN", "from_env")

    assert load_token("secret_explicit") == "secret_explicit"


def test_dotenv_fallback(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    _write_env(tmp_path, "from_dotenv")
    monkeypatch.delenv("NOTION_TOKEN", raising=False)

    assert load_token() == "from_dotenv"


def test_env_fallback_when_no_dotenv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("NOTION_TOKEN", "from_env")

    assert load_token() == "from_env"


def test_missing_token_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("NOTION_TOKEN", raising=False)

    with pytest.raises(NotionConfigError, match="NOTION_TOKEN"):
        load_token()


def test_client_uses_explicit_token(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("NOTION_TOKEN", raising=False)

    client = NotionClient(token="secret_abc")

    assert client._token == "secret_abc"


def test_client_falls_back_to_dotenv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    _write_env(tmp_path, "from_dotenv")
    monkeypatch.delenv("NOTION_TOKEN", raising=False)

    client = NotionClient()

    assert client._token == "from_dotenv"
