def test_health_unauthenticated(temp_hub):
    client, _ = temp_hub
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "hub"}


def test_create_and_list_artifact(temp_hub, auth_headers):
    client, _ = temp_hub
    payload = {
        "html": "<html><body><h1>Hello</h1></body></html>",
        "title": "Hello Report",
        "visibility": "private",
        "tags": ["demo"],
        "project": "hub",
    }
    created = client.post("/api/artifacts", json=payload, headers=auth_headers)
    assert created.status_code == 200
    body = created.json()
    assert body["title"] == "Hello Report"
    assert body["owner"] == "alice@example.com"
    assert body["url"].startswith("https://alice.tailnet.ts.net/a/")

    listed = client.get("/api/artifacts?scope=mine", headers=auth_headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1


def test_edit_html_in_place_keeps_id(temp_hub, auth_headers):
    client, _ = temp_hub
    created = client.post(
        "/api/artifacts",
        json={"html": "<h1>v1</h1>", "title": "T", "visibility": "shareable"},
        headers=auth_headers,
    )
    aid = created.json()["id"]
    size1 = created.json()["size_bytes"]

    patched = client.patch(
        f"/api/artifacts/{aid}",
        json={"html": "<h1>v2 with more content</h1>", "title": "T2"},
        headers=auth_headers,
    )
    assert patched.status_code == 200
    assert patched.json()["id"] == aid  # same id => same URL
    assert patched.json()["title"] == "T2"
    assert patched.json()["size_bytes"] != size1

    raw = client.get(f"/a/{aid}/raw", headers=auth_headers)
    assert "v2 with more content" in raw.text
    assert ">v1<" not in raw.text


def test_private_hidden_from_other_user(temp_hub, auth_headers):
    client, _ = temp_hub
    created = client.post(
        "/api/artifacts",
        json={
            "html": "<html><body>secret</body></html>",
            "title": "Secret",
            "visibility": "private",
        },
        headers=auth_headers,
    )
    artifact_id = created.json()["id"]

    bob_headers = {"Tailscale-User-Login": "bob@example.com"}
    denied = client.get(f"/api/artifacts/{artifact_id}", headers=bob_headers)
    assert denied.status_code == 403


def test_shareable_visible_to_other_user(temp_hub, auth_headers):
    client, _ = temp_hub
    created = client.post(
        "/api/artifacts",
        json={
            "html": "<html><body>shared</body></html>",
            "title": "Shared",
            "visibility": "shareable",
        },
        headers=auth_headers,
    )
    artifact_id = created.json()["id"]

    bob_headers = {"Tailscale-User-Login": "bob@example.com"}
    response = client.get(f"/api/artifacts/{artifact_id}", headers=bob_headers)
    assert response.status_code == 200


def test_update_visibility(temp_hub, auth_headers):
    client, _ = temp_hub
    created = client.post(
        "/api/artifacts",
        json={
            "html": "<html><body>toggle</body></html>",
            "title": "Toggle",
            "visibility": "private",
        },
        headers=auth_headers,
    )
    artifact_id = created.json()["id"]

    updated = client.patch(
        f"/api/artifacts/{artifact_id}",
        json={"visibility": "shareable"},
        headers=auth_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["visibility"] == "shareable"


def test_delete_artifact(temp_hub, auth_headers):
    client, data_dir = temp_hub
    created = client.post(
        "/api/artifacts",
        json={
            "html": "<html><body>delete me</body></html>",
            "title": "Delete",
            "visibility": "private",
        },
        headers=auth_headers,
    )
    artifact_id = created.json()["id"]
    assert (data_dir / "artifacts" / f"{artifact_id}.html").exists()

    deleted = client.delete(f"/api/artifacts/{artifact_id}", headers=auth_headers)
    assert deleted.status_code == 204
    assert not (data_dir / "artifacts" / f"{artifact_id}.html").exists()


def test_raw_artifact_allows_scripts_in_sandbox(temp_hub, auth_headers):
    client, _ = temp_hub
    created = client.post(
        "/api/artifacts",
        json={
            "html": "<html><body><pre class='mermaid'>graph LR; A-->B</pre></body></html>",
            "title": "Diagram",
            "visibility": "private",
        },
        headers=auth_headers,
    )
    artifact_id = created.json()["id"]

    response = client.get(f"/a/{artifact_id}/raw", headers=auth_headers)
    assert response.status_code == 200
    assert response.headers.get("content-security-policy") == "sandbox allow-scripts allow-same-origin"


def test_dashboard_delete_returns_no_content(temp_hub, auth_headers):
    client, _ = temp_hub
    created = client.post(
        "/api/artifacts",
        json={
            "html": "<html><body>gone</body></html>",
            "title": "Gone",
            "visibility": "private",
        },
        headers=auth_headers,
    )
    artifact_id = created.json()["id"]

    deleted = client.delete(f"/a/{artifact_id}", headers=auth_headers)
    assert deleted.status_code == 204
    assert deleted.text == ""