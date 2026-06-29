"""Enhance stored report HTML for reliable in-Hub rendering."""

from __future__ import annotations

import re

_MERMAID_BLOCK_RE = re.compile(
    r"(<(?:pre|div)[^>]*class=[\"'][^\"']*mermaid[^\"']*[\"'][^>]*>)(.*?)(</(?:pre|div)>)",
    re.I | re.S,
)
_MERMAID_SCRIPT_RE = re.compile(
    r"<script[^>]*src=[\"'][^\"']*mermaid[^\"']*[\"'][^>]*>\s*</script>",
    re.I,
)
_MERMAID_INIT_RE = re.compile(
    r"<script>\s*mermaid\.initialize\([\s\S]*?</script>",
    re.I,
)
_MERMAID_MARKER_RE = re.compile(
    r'class=["\'][^"\']*mermaid[^"\']*["\']|'
    r"```mermaid|"
    r"\b(?:flowchart|graph|sequenceDiagram|erDiagram|classDiagram)\b",
    re.I,
)
_BARE_AMP_RE = re.compile(r"&(?!amp;|lt;|gt;|quot;|apos;|#\d+;|#x[\da-fA-F]+;)")

_MERMAID_BOOTSTRAP = """<script src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"></script>
<script>
(function () {
  function runMermaid() {
    if (typeof mermaid === "undefined") return;
    mermaid.initialize({
      startOnLoad: false,
      theme: window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "neutral",
      securityLevel: "loose",
    });
    mermaid.run({ querySelector: ".mermaid" }).catch(function (err) {
      console.error("Mermaid render failed:", err);
    });
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", runMermaid);
  } else {
    runMermaid();
  }
})();
</script>"""


def _needs_mermaid(html: str) -> bool:
    return bool(_MERMAID_MARKER_RE.search(html))


def _fix_mermaid_ampersands(html: str) -> str:
    """Escape bare & in mermaid blocks so HTML parsing preserves node chains."""

    def fix_block(match: re.Match[str]) -> str:
        opening, inner, closing = match.groups()
        return opening + _BARE_AMP_RE.sub("&amp;", inner) + closing

    return _MERMAID_BLOCK_RE.sub(fix_block, html)


def enhance_report_html(html: str) -> str:
    """Inject a consistent Mermaid bootstrap for reports that include diagrams."""
    if not _needs_mermaid(html):
        return html

    html = _fix_mermaid_ampersands(html)
    html = _MERMAID_SCRIPT_RE.sub("", html)
    html = _MERMAID_INIT_RE.sub("", html)

    if re.search(r"</body>", html, re.I):
        return re.sub(r"</body>", _MERMAID_BOOTSTRAP + "\n</body>", html, count=1, flags=re.I)

    return html + _MERMAID_BOOTSTRAP