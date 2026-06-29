def test_requires_auth_without_credentials(temp_hub, monkeypatch):
    from hub.config import get_settings

    monkeypatch.setenv("HUB_DEV_USER", "")
    get_settings.cache_clear()

    client, _ = temp_hub
    response = client.get("/api/artifacts")
    assert response.status_code == 401


def test_accepts_tailscale_identity_header(temp_hub):
    client, _ = temp_hub
    response = client.get(
        "/api/artifacts",
        headers={"Tailscale-User-Login": "bob@example.com"},
    )
    assert response.status_code == 200


def test_rejects_invalid_token(temp_hub):
    client, _ = temp_hub
    response = client.get(
        "/api/artifacts",
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert response.status_code == 401


def test_dev_user_on_localhost(temp_hub):
    client, _ = temp_hub
    response = client.get("/api/artifacts?scope=mine")
    assert response.status_code == 200