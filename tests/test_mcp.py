import json
from unittest.mock import MagicMock, patch

from hub_mcp.server import get_report_url, list_reports, post_report, set_report_visibility


@patch("hub_mcp.server._request")
def test_post_report(mock_request):
    mock_request.return_value = {
        "id": "abc123",
        "url": "https://alice.tailnet.ts.net/a/abc123",
        "title": "Demo",
        "visibility": "private",
    }
    with patch.dict("os.environ", {"HUB_API_TOKEN": "token"}):
        result = post_report("<html></html>", "Demo")
    payload = json.loads(result)
    assert payload["id"] == "abc123"
    mock_request.assert_called_once()


@patch("hub_mcp.server._request")
def test_list_reports(mock_request):
    mock_request.return_value = []
    with patch.dict("os.environ", {"HUB_API_TOKEN": "token"}):
        result = list_reports(scope="mine")
    assert json.loads(result) == []


@patch("hub_mcp.server._request")
def test_set_report_visibility(mock_request):
    mock_request.return_value = {"visibility": "shareable"}
    with patch.dict("os.environ", {"HUB_API_TOKEN": "token"}):
        result = set_report_visibility("abc123", "shareable")
    assert json.loads(result)["visibility"] == "shareable"


@patch("hub_mcp.server._request")
def test_get_report_url(mock_request):
    mock_request.return_value = {"url": "https://alice.tailnet.ts.net/a/abc123"}
    with patch.dict("os.environ", {"HUB_API_TOKEN": "token"}):
        url = get_report_url("abc123")
    assert url == "https://alice.tailnet.ts.net/a/abc123"