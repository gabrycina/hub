from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="HUB_", env_file=".env", extra="ignore")

    data_dir: Path = Path.home() / ".config" / "hub" / "data"
    host: str = "127.0.0.1"
    port: int = 8080
    owner: str = "local@dev"
    api_token: str = ""
    public_url: str = "http://127.0.0.1:8080"
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