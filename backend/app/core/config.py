from __future__ import annotations

import re

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


DEFAULT_SECRET_KEY = "change-me-in-production-use-a-long-random-string"


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


settings = Settings()
