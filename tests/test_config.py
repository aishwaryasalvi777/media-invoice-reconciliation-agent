"""Tests for the settings in config.py.

Each test ignores the private .env file (_env_file=None), so the results are
the same on every computer, whatever someone has in their own .env.
"""

import pytest
from pydantic import ValidationError

from invoice_recon.config import PROJECT_ROOT, Settings


def test_defaults_load() -> None:
    settings = Settings(_env_file=None)

    assert settings.data_folder == PROJECT_ROOT / "data" / "sample"
    assert settings.log_level == "INFO"


def test_a_setting_can_be_overridden(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INVOICE_RECON_LOG_LEVEL", "DEBUG")

    assert Settings(_env_file=None).log_level == "DEBUG"


@pytest.mark.parametrize(
    ("name", "bad_value"),
    [
        ("INVOICE_RECON_DATA_FOLDER", "data/folder-that-does-not-exist"),
        ("INVOICE_RECON_LOG_LEVEL", "LOUD"),
    ],
)
def test_a_wrong_value_is_rejected(
    monkeypatch: pytest.MonkeyPatch, name: str, bad_value: str
) -> None:
    monkeypatch.setenv(name, bad_value)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)
