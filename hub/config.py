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
    # Server mode: when true, the network boundary is the access control, so anyone
    # who can reach the server may view shareable reports even without a Tailscale
    # identity header (e.g. Hub on a devbox reached by VPC IP, not via Tailscale
    # Serve). Publishing still requires the API token; private reports stay owner-only.
    trust_network: bool = False
    # Optional branding shown in the dashboard title (e.g. "Gen AI" -> "Gen AI Hub").
    site_name: str = ""
    max_upload_bytes: int = 5 * 1024 * 1024

    @property
    def brand_name(self) -> str:
        return f"{self.site_name} Hub" if self.site_name else "Your Hub"

    @property
    def artifacts_dir(self) -> Path:
        return self.data_dir / "artifacts"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "hub.db"


@lru_cache
def get_settings() -> Settings:
    return Settings()