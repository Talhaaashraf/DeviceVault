from __future__ import annotations

import os
import re
import secrets
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


LATEST_OS_VERSIONS = {
    "ios": 18,
    "android": 15,
    "watchos": 11,
    "wear_os": 5,
}


def os_freshness_category(os_type: str | None, os_version: str | None) -> str:
    if not os_type or not os_version:
        return "Unknown"

    os_type_key = str(os_type).strip().lower()
    latest = LATEST_OS_VERSIONS.get(os_type_key)
    if latest is None:
        return "Unknown"

    match = re.search(r"(\d+)", os_version)
    if not match:
        return "Unknown"

    try:
        major = int(match.group(1))
    except ValueError:
        return "Unknown"

    delta = latest - major
    if delta <= 0:
        return "Latest"
    if delta <= 2:
        return "Recent"
    return "Outdated"


# Placeholder from .env.example; never used to sign tokens (see _resolve_secret_key)
DEFAULT_SECRET_KEY = "change-me-in-production-use-a-long-random-string"  # nosec B105

# Where an auto-generated key is kept when none is configured (git-ignored)
SECRET_KEY_FILE = Path(__file__).resolve().parents[2] / ".secret_key"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "sqlite:///./device_inventory.db"
    SECRET_KEY: str = DEFAULT_SECRET_KEY
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"
    SEED_ON_STARTUP: bool = True

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


def _resolve_secret_key(configured: str, key_file: Path = SECRET_KEY_FILE) -> tuple[str, bool]:
    """Return (key, auto_generated).

    A missing or placeholder SECRET_KEY must never be used: anyone could forge tokens with the
    published value. Instead a random key is generated once and persisted next to the backend.
    """
    if configured and configured != DEFAULT_SECRET_KEY:
        return configured, False
    if key_file.exists():
        stored = key_file.read_text(encoding="utf-8").strip()
        if stored:
            return stored, True
    key = secrets.token_urlsafe(48)
    key_file.write_text(key, encoding="utf-8")
    try:
        os.chmod(key_file, 0o600)
    except OSError:
        pass
    return key, True


settings = Settings()
settings.SECRET_KEY, SECRET_KEY_AUTO_GENERATED = _resolve_secret_key(settings.SECRET_KEY)
