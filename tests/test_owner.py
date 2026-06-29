from hub.auth import AuthContext
from hub.config import Settings
from hub.owner import resolved_owner


def test_resolved_owner_prefers_config(monkeypatch):
    monkeypatch.delenv("HUB_OWNER", raising=False)
    settings = Settings(owner="alice@example.com")
    assert resolved_owner(settings) == "alice@example.com"


def test_resolved_owner_falls_back_from_local_dev(monkeypatch):
    monkeypatch.delenv("HUB_OWNER", raising=False)
    monkeypatch.setattr("hub.owner.detect_owner", lambda: "c.gabriele.info@gmail.com")
    settings = Settings(owner="local@dev")
    assert resolved_owner(settings) == "c.gabriele.info@gmail.com"


def test_resolved_owner_uses_auth_when_config_empty(monkeypatch):
    monkeypatch.delenv("HUB_OWNER", raising=False)
    monkeypatch.setattr("hub.owner.detect_owner", lambda: "local@dev")
    settings = Settings(owner="")
    auth = AuthContext(user="c.gabriele.info@gmail.com", is_owner=True, via_token=False)
    assert resolved_owner(settings, auth) == "c.gabriele.info@gmail.com"