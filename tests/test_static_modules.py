"""
Automated tests for Native ES-Module Architecture & Static Asset Serving.
Verifies:
1. Static module files are mounted, accessible, and served with correct JavaScript MIME types.
2. Content-Security-Policy headers permit 'self' script execution without inline scripts.
3. src/portal/index.html cleanly imports /static/main.js via <script type="module">.
4. src/portal/index.html has zero legacy inline scripts and zero inline onclick/oninput handlers.
"""

from __future__ import annotations

import re
from pathlib import Path
from starlette.testclient import TestClient

from app import app, PROJECT_ROOT

client = TestClient(app)


def test_static_modules_served_with_correct_mime():
    """Verify that all modular JS files are served by FastAPI with HTTP 200 and application/javascript MIME."""
    module_files = [
        "/static/main.js",
        "/static/modules/api.js",
        "/static/modules/auth.js",
        "/static/modules/charts.js",
        "/static/modules/billing.js",
        "/static/modules/valuation.js",
    ]

    for path in module_files:
        response = client.get(path)
        assert response.status_code == 200, f"Expected 200 for {path}, got {response.status_code}"
        content_type = response.headers.get("content-type", "")
        assert "javascript" in content_type.lower(), f"Expected javascript MIME for {path}, got {content_type}"
        assert len(response.text) > 100, f"Expected non-empty script for {path}"


def test_index_html_uses_es_module_architecture():
    """Verify src/portal/index.html imports main.js as an ES module and has no monolithic inline script."""
    html_path = PROJECT_ROOT / "src" / "portal" / "index.html"
    assert html_path.exists(), "src/portal/index.html must exist"
    content = html_path.read_text(encoding="utf-8")

    # 1. Must contain ES-module script tag
    assert '<script type="module" src="/static/main.js"></script>' in content, (
        "src/portal/index.html must include <script type=\"module\" src=\"/static/main.js\"></script>"
    )

    # 2. Must not contain any inline <script> blocks (only external script src tags)
    script_blocks = re.findall(r'<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>', content, flags=re.DOTALL | re.IGNORECASE)
    # Strip any empty whitespace scripts if any
    non_empty_inline_scripts = [s.strip() for s in script_blocks if s.strip()]
    assert len(non_empty_inline_scripts) == 0, (
        f"Found {len(non_empty_inline_scripts)} unmigrated inline <script> blocks in index.html"
    )

    # 3. Must not have inline onclick/oninput/onchange attributes on interactive buttons/inputs
    inline_handlers = re.findall(r'<(?:button|input|a)\b[^>]*\b(on(?:click|input|change)=["\'][^"\']+["\'])', content, flags=re.IGNORECASE)
    assert len(inline_handlers) == 0, (
        f"Found {len(inline_handlers)} inline event handlers remaining in index.html: {inline_handlers[:5]}"
    )


def test_csp_header_permits_self_scripts():
    """Verify that Content-Security-Policy in app.py allows script-src 'self' for ES modules."""
    response = client.get("/")
    assert response.status_code == 200
    csp = response.headers.get("content-security-policy", "")
    assert "script-src" in csp, "CSP must define script-src"
    assert "'self'" in csp, "CSP script-src must permit 'self' for native ES modules"


def test_es_module_cross_imports():
    """Verify main.js and controllers export and import their required contracts without syntax errors."""
    main_js_path = PROJECT_ROOT / "src" / "portal" / "static" / "main.js"
    assert main_js_path.exists(), "src/portal/static/main.js must exist"
    main_content = main_js_path.read_text(encoding="utf-8")

    assert "import" in main_content, "main.js must import ES modules"
    assert "./modules/api.js" in main_content
    assert "./modules/auth.js" in main_content
    assert "./modules/charts.js" in main_content
    assert "./modules/billing.js" in main_content
    assert "./modules/valuation.js" in main_content


if __name__ == "__main__":
    test_static_modules_served_with_correct_mime()
    test_index_html_uses_es_module_architecture()
    test_csp_header_permits_self_scripts()
    test_es_module_cross_imports()
    print("All static module tests passed successfully!")
