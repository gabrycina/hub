from hub.tailscale_serve import (
    is_serve_configured,
    parse_enable_url,
    resolve_enable_url,
    setup_tailscale_serve,
    tailscale_enable_url,
)


def test_parse_enable_url():
    output = """
Serve is not enabled on your tailnet.
To enable, visit:

         https://login.tailscale.com/f/serve?node=njEcC5S3FD21CNTRL
"""
    assert (
        parse_enable_url(output)
        == "https://login.tailscale.com/f/serve?node=njEcC5S3FD21CNTRL"
    )


def test_tailscale_enable_url_from_status(monkeypatch):
    monkeypatch.setattr(
        "hub.tailscale_serve._tailscale_self",
        lambda: {"ID": "njEcC5S3FD21CNTRL", "DNSName": "machine.ts.net."},
    )
    assert (
        tailscale_enable_url()
        == "https://login.tailscale.com/f/serve?node=njEcC5S3FD21CNTRL"
    )


def test_resolve_enable_url_falls_back_to_status(monkeypatch):
    monkeypatch.setattr(
        "hub.tailscale_serve._tailscale_self",
        lambda: {"ID": "abc123", "DNSName": "machine.ts.net."},
    )
    assert resolve_enable_url("timeout") == "https://login.tailscale.com/f/serve?node=abc123"


def test_is_serve_configured_no_output(monkeypatch):
    monkeypatch.setattr(
        "hub.tailscale_serve.serve_status_output",
        lambda: "No serve config",
    )
    assert is_serve_configured() is False


def test_setup_tailscale_serve_local_without_tailscale(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("PATH", "")

    import hub.paths as paths

    config_dir = tmp_path / "config"
    monkeypatch.setattr(paths, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(paths, "CONFIG_ENV", config_dir / "config.env")
    config_dir.mkdir(parents=True)

    result = setup_tailscale_serve(wait_seconds=0, open_browser=False)
    assert result.state == "local_only"
    assert result.public_url.startswith("http://")


def test_setup_tailscale_serve_returns_enable_url_on_timeout(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr("hub.tailscale_serve.is_serve_configured", lambda: False)
    monkeypatch.setattr(
        "hub.tailscale_serve._attempt_serve",
        lambda port, timeout=5.0: type(
            "Result",
            (),
            {"returncode": 124, "stdout": "", "stderr": "timeout"},
        )(),
    )
    monkeypatch.setattr(
        "hub.tailscale_serve._tailscale_self",
        lambda: {"ID": "node42", "DNSName": "machine.ts.net."},
    )
    monkeypatch.setattr(
        "hub.tailscale_serve.shutil.which",
        lambda name: "/usr/bin/tailscale" if name == "tailscale" else None,
    )

    import hub.paths as paths

    config_dir = tmp_path / "config"
    monkeypatch.setattr(paths, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(paths, "CONFIG_ENV", config_dir / "config.env")
    config_dir.mkdir(parents=True)

    result = setup_tailscale_serve(wait_seconds=0, open_browser=False)
    assert result.state == "needs_enable"
    assert result.enable_url == "https://login.tailscale.com/f/serve?node=node42"