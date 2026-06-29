import json
import os
from typing import Any

import httpx
from fastmcp import FastMCP

from hub.bootstrap import ensure_hub_running, load_config_env
from hub.constants import DEFAULT_HOST, DEFAULT_PORT

HUB_INSTRUCTIONS = """\
Hub is a shared report inbox for AI agents. You publish self-contained HTML
reports — docs, data reviews, postmortems, architecture notes, shared context
for other agents — and get back a stable URL anyone on the same network can open.

Tools:
- post_report: publish a NEW report; returns its url.
- update_report: revise an EXISTING report in place (same url). Prefer this over
  post_report when iterating on something you already published.
- list_reports / get_report_url / set_report_visibility: browse and manage.

When you generate a substantial HTML artifact worth sharing, offer to publish it.

After post_report or update_report returns a url, OPEN IT in the user's default
browser so it pops up immediately (macOS: `open <url>`; Linux: `xdg-open <url>`;
Windows: `start <url>`), and copy it to the clipboard where possible (macOS:
`printf %s <url> | pbcopy`). Do this by default unless the user has said they
don't want reports auto-opened.
"""

mcp = FastMCP("Hub", instructions=HUB_INSTRUCTIONS)


def _hub_url() -> str:
    load_config_env()
    host = os.environ.get("HUB_HOST", DEFAULT_HOST)
    port = os.environ.get("HUB_PORT", str(DEFAULT_PORT))
    return os.environ.get("HUB_URL", f"http://{host}:{port}").rstrip("/")


def _api_token() -> str:
    load_config_env()
    token = os.environ.get("HUB_API_TOKEN", "")
    if not token:
        raise RuntimeError(
            "Hub is not configured. Run `uv run hub init --mcp` once, then restart your agent."
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


def update_report(
    report_id: str,
    html: str | None = None,
    title: str | None = None,
    visibility: str | None = None,
    tags: list[str] | None = None,
    project: str | None = None,
) -> str:
    """Edit an existing report in place. Keeps the same id and URL — use this to
    revise a report instead of publishing a new one. Only the fields you pass change."""
    payload: dict[str, Any] = {}
    if html is not None:
        payload["html"] = html
    if title is not None:
        payload["title"] = title
    if visibility is not None:
        payload["visibility"] = visibility
    if tags is not None:
        payload["tags"] = tags
    if project is not None:
        payload["project"] = project
    result = _request("PATCH", f"/api/artifacts/{report_id}", json=payload)
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
mcp.tool(update_report)
mcp.tool(list_reports)
mcp.tool(set_report_visibility)
mcp.tool(get_report_url)


def cli() -> None:
    # When pointed at a remote Hub (HUB_URL set, e.g. a devbox), don't start a
    # local server — just act as a client to the remote instance.
    if not os.environ.get("HUB_URL"):
        ensure_hub_running()
    mcp.run()


if __name__ == "__main__":
    cli()