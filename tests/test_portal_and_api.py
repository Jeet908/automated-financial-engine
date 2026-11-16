"""
Comprehensive integration tests for Subagent B:
- Client portal (GET / and GET /portal)
- API health check (GET /api/v1/health)
- Zero-click Valuation Pack Generation (POST /api/v1/model/generate-pack)
- Dynamic download route (GET /api/v1/model/download/{filename}) for .zip, .xlsx, .pdf, .pptx
- Verification of WordPress embed & Portal HTML
"""

import os
from pathlib import Path
from fastapi.testclient import TestClient
from src.ingestion.api import app

client = TestClient(app)

def test_portal_routes():
    # GET /
    r1 = client.get("/")
    assert r1.status_code == 200
    assert "text/html" in r1.headers.get("content-type", "")
    assert "MarketLens Analytics" in r1.text
    assert "/api/v1/model/generate-pack" in r1.text

    # GET /portal
    r2 = client.get("/portal")
    assert r2.status_code == 200
    assert "text/html" in r2.headers.get("content-type", "")
    assert r2.content == r1.content

def test_health():
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["service"] == "financial-modeling-engine"

def test_generate_pack_endpoint():
    sample_file = Path("inputs/clean_infosys_ind_as.xlsx")
    assert sample_file.exists(), f"Sample file {sample_file} not found"

    with open(sample_file, "rb") as f:
        resp = client.post(
            "/api/v1/model/generate-pack",
            files={"file": (sample_file.name, f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )

    assert resp.status_code == 200, f"Error {resp.status_code}: {resp.text}"
    data = resp.json()

    # Validate schema
    assert data["status"] == "success"
    assert "pack_filename" in data
    assert data["pack_filename"].endswith(".zip")
    assert "zip_download_url" in data
    assert "xlsx_download_url" in data
    assert "pdf_download_url" in data
    assert "pptx_download_url" in data

    # Validate metadata
    assert "metadata" in data
    meta = data["metadata"]
    assert "name" in meta
    assert "currency" in meta
    assert "standard" in meta

    # Validate preview dict
    assert "preview" in data
    prev = data["preview"]
    assert "ev_base" in prev
    assert "equity_base" in prev
    assert "ev_bull" in prev
    assert "ev_bear" in prev
    assert "price_per_share" in prev

    # Test file downloads and MIME types
    dl_zip = client.get(data["zip_download_url"])
    assert dl_zip.status_code == 200
    assert dl_zip.headers.get("content-type") == "application/zip"

    dl_xlsx = client.get(data["xlsx_download_url"])
    assert dl_xlsx.status_code == 200
    assert "spreadsheetml" in dl_xlsx.headers.get("content-type", "")

    dl_pdf = client.get(data["pdf_download_url"])
    assert dl_pdf.status_code == 200
    assert dl_pdf.headers.get("content-type") == "application/pdf"

    dl_pptx = client.get(data["pptx_download_url"])
    assert dl_pptx.status_code == 200
    assert "presentationml" in dl_pptx.headers.get("content-type", "")

def test_wordpress_embed_html():
    embed_path = Path("src/portal/wordpress_saaslauncher_embed.html")
    assert embed_path.exists()
    content = embed_path.read_text(encoding="utf-8")
    assert "MarketLens" in content
    assert "/api/v1/model/generate-pack" in content
    assert "app.marketlensanalytics.in" in content
    assert "www.marketlensanalytics.in" in content

if __name__ == "__main__":
    test_portal_routes()
    test_health()
    test_generate_pack_endpoint()
    test_wordpress_embed_html()
    print("ALL SUBAGENT B TESTS PASSED SUCCESSFULLY!")
