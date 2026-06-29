import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from hub.config import get_settings
from hub.main import create_app


@pytest.fixture
def temp_hub(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    data_dir = tmp_path / "data"
    monkeypatch.setenv("HUB_DATA_DIR", str(data_dir))
    monkeypatch.setenv("HUB_OWNER", "alice@example.com")
    monkeypatch.setenv("HUB_API_TOKEN", "test-token-secret")
    monkeypatch.setenv("HUB_PUBLIC_URL", "https://alice.tailnet.ts.net")
    monkeypatch.setenv("HUB_DEV_USER", "alice@example.com")

    get_settings.cache_clear()
    app = create_app()
    client = TestClient(app)
    yield client, data_dir
    get_settings.cache_clear()


@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer test-token-secret"}