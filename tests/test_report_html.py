from hub.report_html import enhance_report_html


def test_enhance_fixes_mermaid_ampersands_and_injects_runner():
    html = """<!DOCTYPE html><html><body>
<pre class="mermaid">
flowchart TD
A --> B & C
</pre>
<script src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"></script>
<script>mermaid.initialize({ startOnLoad: true });</script>
</body></html>"""

    out = enhance_report_html(html)

    assert "A --> B &amp; C" in out
    assert "mermaid.run({ querySelector: \".mermaid\" })" in out
    assert "startOnLoad: false" in out
    assert out.count("mermaid.min.js") == 1


def test_enhance_passthrough_without_mermaid():
    html = "<html><body><p>Hello</p></body></html>"
    assert enhance_report_html(html) == html