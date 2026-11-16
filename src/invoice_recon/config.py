"""Project settings: one place for values that change between computers.

Values are read, in this order of priority:
1. environment variables, for example INVOICE_RECON_LOG_LEVEL=DEBUG
2. the private .env file in the project folder (never committed)
3. the defaults below

Secrets (API keys, passwords) must only ever come from 1 or 2, never from code.
"""

from pathlib import Path
from typing import Literal

from pydantic import DirectoryPath, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="INVOICE_RECON_",
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    data_folder: DirectoryPath = PROJECT_ROOT / "data" / "sample"
    """Folder holding the media plan, delivery, contracts and invoices. Must exist."""

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    """How much detail the app prints: DEBUG is the most, ERROR the least."""

    @field_validator("data_folder", mode="before")
    @classmethod
    def relative_to_project(cls, value: str | Path) -> Path:
        """Read a relative path like 'data/sample' from the project folder,
        so it works no matter which folder the app is started from."""
        path = Path(value)
        return path if path.is_absolute() else PROJECT_ROOT / path


def get_settings() -> Settings:
    return Settings()
