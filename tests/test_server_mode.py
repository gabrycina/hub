from hub.auth import can_view
from hub.config import Settings


def test_shareable_requires_viewer_by_default():
    # Local/Serve mode: anonymous (no identity header) cannot view.
    assert can_view(visibility="shareable", owner="a@x", viewer=None) is False
    assert can_view(visibility="shareable", owner="a@x", viewer="b@x") is True


def test_shareable_open_when_trust_network():
    # Server mode: the network is the boundary, so anonymous can view shareable.
    assert can_view(
        visibility="shareable", owner="a@x", viewer=None, trust_network=True
    ) is True


def test_private_stays_owner_only_even_with_trust_network():
    assert can_view(
        visibility="private", owner="a@x", viewer=None, trust_network=True
    ) is False
    assert can_view(
        visibility="private", owner="a@x", viewer="b@x", trust_network=True
    ) is False
    assert can_view(
        visibility="private", owner="a@x", viewer="a@x", trust_network=True
    ) is True


def test_brand_name_default_and_custom():
    assert Settings(site_name="").brand_name == "Your Hub"
    assert Settings(site_name="Gen AI").brand_name == "Gen AI Hub"
