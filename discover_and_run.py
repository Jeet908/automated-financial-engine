"""
discover_and_run.py — Zero-Touch Autonomous Live Web Scraping & Multi-Engine Execution Pipeline.

Usage:
    python discover_and_run.py [--domain "<sector>"] [--market "india|us|global|random"]
"""

from __future__ import annotations

import argparse
import os
import sys
import json
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.ingestion.live_web_scraper import LiveWebScraper, DOMAIN_CATALOG
from financial_engine.cli import run_pipeline
from src.cli import process_file


def run_discovery_pipeline(
    domain: str | None = None,
    market: str = "random",
    mc_iterations: int = 10000,
    quiet: bool = False,
    workspace_root: str | Path | None = None,
) -> dict:
    """
    Executes the entire end-to-end zero-touch pipeline:
    1. Scrapes live multi-statement company data by domain.
    2. Exports client_inbox/<Ticker>_Live_Scraped.xlsx and inputs/<ticker>_live_config.json.
    3. Runs Engine A (Deep Stochastic & Interactive Dashboard Suite).
    4. Runs Engine B (Client Executive Pack: .xlsx, .pdf, .pptx, .zip).
    5. Returns unified paths and valuation summaries.
    """
    if not quiet:
        print("=" * 80)
        print("   ZERO-TOUCH AUTONOMOUS FINANCIAL DISCOVERY & VALUATION PIPELINE")
        print("   Real-World Financial Scraping, 3-Statement Modeling & Executive Packaging")
        print("=" * 80)

    # -------------------------------------------------------------
    # Step 1: Scrape & Auto-Adapt Financial Statements
    # -------------------------------------------------------------
    if not quiet:
        print(f"[*] Step 1: Querying sector indices for domain: '{domain or 'Random Auto-Select'}'...")

    workspace = Path(workspace_root).resolve() if workspace_root else PROJECT_ROOT
    scraper = LiveWebScraper(
        output_inbox=str(workspace / "client_inbox"),
        output_inputs=str(workspace / "inputs"),
    )
    company_data, xlsx_inbox_path, json_config_path = scraper.discover_and_extract(
        domain=domain,
        market=market,
    )

    ticker = company_data["ticker"]
    ticker_slug = ticker.replace(".NS", "").lower()
    comp_name = company_data["name"]

    if not quiet:
        print(f"[OK] Discovered real listed entity: {comp_name} ({ticker})")
        print(f"[+] Saved scraped client workbook: {xlsx_inbox_path}")
        print(f"[+] Calibrated financial engine config: {json_config_path}")

    # -------------------------------------------------------------
    # Step 2: Trigger Engine A (Financial Engine Suite)
    # -------------------------------------------------------------
    artifacts_dir = workspace / "artifacts" / f"{ticker_slug}_live"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    if not quiet:
        print(f"\n[*] Step 2A: Launching Deep Stochastic Engine A (10,000 Monte Carlo Iterations)...")

    model = run_pipeline(
        config_path=str(json_config_path),
        output_dir=str(artifacts_dir),
        mc_iterations=mc_iterations,
        export_excel=True,
        export_html=True,
        export_memo=True,
        export_json=True,
        quiet=quiet,
    )

    # Check accounting invariants
    cert = model.audit_certificate
    if not cert.is_valid:
        raise ValueError(f"Accounting verification failed for {ticker}!")

    if not quiet:
        max_error = max((check.max_discrepancy for check in cert.checks), default=0.0)
        print(f"[OK] Engine A Invariants Verified: Max Error = {max_error:.6e}.")

    # -------------------------------------------------------------
    # Step 3: Trigger Engine B (Client Executive Pack)
    # -------------------------------------------------------------
    outbox_dir = workspace / "client_outbox" / f"{ticker_slug}_live"
    outbox_dir.mkdir(parents=True, exist_ok=True)

    if not quiet:
        print(f"\n[*] Step 2B: Launching Client Executive Pack Engine B (XLSX, PDF, PPTX, ZIP)...")

    pack_res = process_file(
        file_path=str(xlsx_inbox_path),
        output_dir=str(outbox_dir),
    )

    if not quiet:
        print(f"[OK] Engine B Compiled 3-Deliverable Executive Pack into: {outbox_dir}")
        print("\n" + "=" * 80)
        print(f" PIPELINE COMPLETE: {comp_name} ({ticker})")
        print(f" Intrinsic Value per Share: {model.config.metadata.currency.value} {model.value_per_share:.2f}")
        print(f" Scraped Market Price:      {model.config.metadata.currency.value} {company_data['current_market_price']:.2f}")
        print(f" Interactive Dashboard:     {artifacts_dir / f'{ticker_slug}_dashboard.html'}")
        print(f" Client Valuation Pack:     {pack_res.get('zip_path')}")
        print("=" * 80 + "\n")

    return {
        "company": company_data,
        "ticker_slug": ticker_slug,
        "engine_a_model": model,
        "engine_b_pack": pack_res,
        "paths": {
            "scraped_xlsx": str(xlsx_inbox_path),
            "config_json": str(json_config_path),
            "dashboard_html": str(artifacts_dir / f"{ticker_slug}_dashboard.html"),
            "memo_md": str(artifacts_dir / f"{ticker_slug}_investment_memo.md"),
            "audit_cert_json": str(artifacts_dir / f"{ticker_slug}_audit_certificate.json"),
            "engine_a_xlsx": str(artifacts_dir / f"{ticker_slug}_financial_model.xlsx"),
            "pack_xlsx": pack_res.get("xlsx_path"),
            "pack_pdf": pack_res.get("pdf_path"),
            "pack_pptx": pack_res.get("pptx_path"),
            "pack_zip": pack_res.get("zip_path"),
        }
    }


def main():
    parser = argparse.ArgumentParser(description="Zero-Touch Live Financial Scraping & Valuation")
    parser.add_argument("--domain", type=str, default=None, help="Target sector or industry domain")
    parser.add_argument("--market", type=str, default="random", choices=["india", "us", "global", "random"], help="Market exchange focus")
    parser.add_argument("--mc-iterations", type=int, default=10000, help="Monte Carlo iterations")
    parser.add_argument("--quiet", action="store_true", help="Quiet output")

    args = parser.parse_args()
    run_discovery_pipeline(
        domain=args.domain,
        market=args.market,
        mc_iterations=args.mc_iterations,
        quiet=args.quiet,
    )


if __name__ == "__main__":
    main()
