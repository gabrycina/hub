from hub.tailscale_serve import (
    is_serve_configured,
    parse_enable_url,
    setup_tailscale_serve,
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