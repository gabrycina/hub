import json
import os
from typing import Any

import httpx
from fastmcp import FastMCP

from hub.bootstrap import ensure_hub_running, load_config_env

mcp = FastMCP("Hub")


def _hub_url() -> str:
    load_config_env()
    host = os.environ.get("HUB_HOST", "127.0.0.1")
    port = os.environ.get("HUB_PORT", "8080")
    return os.environ.get("HUB_URL", f"http://{host}:{port}").rstrip("/")


def _api_token() -> str:
    load_config_env()
    token = os.environ.get("HUB_API_TOKEN", "")
    if not token:
        raise RuntimeError(
            "Hub is not configured. Run `uv run hub init --mcp` once, then restart Claude Code."
        )
    return token


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {_api_token()}"}


def _request(method: str, path: str, **kwargs: Any) -> Any:
    with httpx.Client(base_url=_hub_url(), headers=_headers(), timeout=30.0) as client:
        response = client.request(method, path, **kwargs)
        response.raise_for_status()
        if response.status_code == 204:
            return None
        return response.json()


def post_report(
    html: str,
    title: str,
    visibility: str = "private",
    tags: list[str] | None = None,
    project: str | None = None,
) -> str:
    """Publish an HTML report to Hub and return the shareable URL."""
    payload = {
        "html": html,
        "title": title,
        "visibility": visibility,
        "tags": tags or [],
        "project": project,
    }
    result = _request("POST", "/api/artifacts", json=payload)
    return json.dumps(result, indent=2)


def list_reports(scope: str = "all", query: str | None = None) -> str:
    """List reports from Hub. Scope: mine, shared, or all."""
    params: dict[str, str] = {"scope": scope}
    if query:
        params["q"] = query
    result = _request("GET", "/api/artifacts", params=params)
    return json.dumps(result, indent=2)


def set_report_visibility(report_id: str, visibility: str) -> str:
    """Set a report to private or shareable."""
    result = _request(
        "PATCH",
        f"/api/artifacts/{report_id}",
        json={"visibility": visibility},
    )
    return json.dumps(result, indent=2)


def get_report_url(report_id: str) -> str:
    """Get the public URL for an existing report."""
    result = _request("GET", f"/api/artifacts/{report_id}")
    return result["url"]


mcp.tool(post_report)
mcp.tool(list_reports)
mcp.tool(set_report_visibility)
mcp.tool(get_report_url)


def cli() -> None:
    ensure_hub_running()
    mcp.run()


if __name__ == "__main__":
    cli()