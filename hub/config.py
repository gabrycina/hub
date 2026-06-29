from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from hub.constants import DEFAULT_LOCAL_URL, DEFAULT_PORT
from hub.paths import CONFIG_ENV


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="HUB_",
        env_file=(CONFIG_ENV, ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    data_dir: Path = Path.home() / ".config" / "hub" / "data"
    host: str = "127.0.0.1"
    port: int = DEFAULT_PORT
    owner: str = "local@dev"
    api_token: str = ""
    public_url: str = DEFAULT_LOCAL_URL
    dev_user: str = ""
    max_upload_bytes: int = 5 * 1024 * 1024

    @property
    def artifacts_dir(self) -> Path:
        return self.data_dir / "artifacts"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "hub.db"


@lru_cache
def get_settings() -> Settings:
    return Settings()