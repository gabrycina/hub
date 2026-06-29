from hub.auth import can_view
from hub.config import Settings


def test_shareable_requires_viewer_by_default():
    # Local/Serve mode: anonymous (no identity header) cannot view.
    assert can_view(visibility="shareable", owner="a@x", viewer=None) is False
    assert can_view(visibility="shareable", owner="a@x", viewer="b@x") is True


def test_trust_network_makes_everything_viewable():
    # Server mode: the network (VPN) is the boundary, so anyone who can reach the
    # server sees every report, regardless of visibility or identity.
    assert can_view(
        visibility="shareable", owner="a@x", viewer=None, trust_network=True
    ) is True
    assert can_view(
        visibility="private", owner="a@x", viewer=None, trust_network=True
    ) is True
    assert can_view(
        visibility="private", owner="a@x", viewer="b@x", trust_network=True
    ) is True


def test_private_stays_owner_only_in_local_mode():
    assert can_view(visibility="private", owner="a@x", viewer=None) is False
    assert can_view(visibility="private", owner="a@x", viewer="b@x") is False
    assert can_view(visibility="private", owner="a@x", viewer="a@x") is True


def test_brand_name_default_and_custom():
    assert Settings(site_name="").brand_name == "Your Hub"
    assert Settings(site_name="Gen AI").brand_name == "Gen AI Hub"


def test_parse_report_id_accepts_id_or_url():
    from hub_mcp.server import _parse_report_id

    assert _parse_report_id("abc123") == "abc123"
    assert _parse_report_id("http://host:8000/a/abc123") == "abc123"
    assert _parse_report_id("http://host:8000/a/abc123/") == "abc123"
    assert _parse_report_id("http://host:8000/a/abc123/raw") == "abc123"
