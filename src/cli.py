"""
Command-Line Interface (CLI) for the Automated Financial Modeling & Valuation Engine.

Usage:
    finmodel run --input <file_or_dir> [--output <dir>]
    py -m src.cli run --input <file_or_dir> [--output <dir>]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Ensure required workspace folders exist
INBOX_DIR = PROJECT_ROOT / "client_inbox"
OUTBOX_DIR = PROJECT_ROOT / "client_outbox"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
INBOX_DIR.mkdir(parents=True, exist_ok=True)
OUTBOX_DIR.mkdir(parents=True, exist_ok=True)
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

from src.ingestion.ingester import UniversalIngester
from src.engine.orchestrator import ModelOrchestrator
from src.exporters.executive_pack import ExecutivePackCompiler
from src.exporters.formula_checker import FormulaChecker

SUPPORTED_EXTS = {".xlsx", ".xls", ".csv", ".json", ".pdf"}


def process_file(
    file_path: str,
    output_dir: str = "outputs",
    scenarios: list[str] | None = None,
    n_years: int = 5,
    metadata_override: dict | None = None,
    valuation_inputs_override: dict | None = None,
) -> dict:
    """
    Ingests financial statement file, runs 3-statement + DCF engine, and
    compiles synchronized 3-deliverable Client Valuation Pack (.xlsx, .pdf, .pptx, .zip).
    """
    if scenarios is None:
        scenarios = ["Base", "Bull", "Bear"]

    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {file_path}")

    print(f"[*] Ingesting: {path.name}")
    # If it's a fixture JSON directly, load it
    if path.suffix.lower() == ".json":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        metadata = data.get("metadata", {"name": path.stem})
        normalized = data
    else:
        ingester = UniversalIngester()
        norm_result = ingester.ingest_file(str(path))
        normalized = norm_result
        metadata = {
            "name": getattr(norm_result, "company_name", None) or path.stem,
            "standard": getattr(norm_result, "standard", "IND_AS"),
            "currency": getattr(norm_result, "currency", "INR"),
            "unit": getattr(norm_result, "unit", "Crores"),
            "fy_end_month": getattr(norm_result, "fiscal_year_end", 3),
        }

    if metadata_override:
        metadata.update(metadata_override)

    print(f"[*] Calibrating drivers & running 3-statement + DCF engine ({', '.join(scenarios)})...")
    orchestrator = ModelOrchestrator()
    engine_output = orchestrator.run(
        normalized,
        scenarios=scenarios,
        n_years=n_years,
        valuation_inputs=valuation_inputs_override,
    )

    os.makedirs(output_dir, exist_ok=True)
    clean_name = "".join(c if c.isalnum() or c in ("_", "-") else "_" for c in metadata.get("name", path.stem))
    if not clean_name:
        clean_name = path.stem

    print(f"[*] Compiling institutional 3-deliverable valuation pack into: {output_dir}")
    compiler = ExecutivePackCompiler()
    pack_res = compiler.compile_pack(
        engine_output=engine_output,
        normalized_financials=normalized,
        metadata=metadata,
        output_dir=output_dir,
        clean_name=clean_name,
    )

    print("[*] Scanning generated formulas for integrity...")
    checker = FormulaChecker()
    check_result = checker.scan(pack_res["xlsx_path"])
    if check_result.has_errors:
        print(f"[!] Warning: Formula errors detected in {pack_res['xlsx_path']}: {check_result.error_cells}")
    else:
        print(f"[+] Workbook verified: {check_result.total_formulas_scanned} formulas checked, 0 errors.")

    print(f"[OK] Successfully generated valuation pack for {path.name}:")
    print(f"    - Excel Model: {pack_res['xlsx_path']}")
    print(f"    - PDF Tear-Sheet: {pack_res['pdf_path']}")
    print(f"    - PowerPoint: {pack_res['pptx_path']}")
    print(f"    - Client Valuation Pack: {pack_res['zip_path']}")

    pack_res["metadata"] = metadata
    pack_res["engine_output"] = engine_output
    return pack_res


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Automated Financial Modeling & Valuation Engine CLI (finmodel)"
    )

    subparsers = parser.add_subparsers(dest="command")

    # Command: run
    run_parser = subparsers.add_parser("run", help="Run ingestion, forecast, and pack compilation")
    _add_run_args(run_parser)

    # Command: watch
    watch_parser = subparsers.add_parser("watch", help="Watch folder for new incoming files")
    watch_parser.add_argument("--watch-dir", default="client_inbox", help="Directory to watch")
    watch_parser.add_argument("--output-dir", "--output", default="client_outbox", help="Directory for compiled packs")
    watch_parser.add_argument("--interval", type=float, default=2.0, help="Polling interval in seconds")

    # Also support direct arguments without 'run' subcommand
    _add_run_args(parser)

    return parser


def _add_run_args(p: argparse.ArgumentParser):
    p.add_argument(
        "--input", "-i", help="Input financial statement file or directory (.xlsx, .xls, .csv, .json, .pdf)"
    )
    p.add_argument(
        "--output", "--output-dir", "-o", dest="output", default=None,
        help="Output directory for generated client valuation packs (.xlsx, .pdf, .pptx, .zip)"
    )
    p.add_argument(
        "--scenarios", "-s", nargs="+", default=["Base", "Bull", "Bear"], help="Scenarios to run"
    )
    p.add_argument(
        "--n-years", "-n", type=int, default=5, help="Number of forecast years"
    )


def main():
    parser = _build_parser()
    args = parser.parse_args()

    # Handle watch command
    if args.command == "watch":
        from src.watcher import run_watcher
        run_watcher(
            watch_dir=args.watch_dir,
            output_dir=args.output_dir,
            poll_interval=args.interval,
        )
        return

    # Handle run command or default
    if not args.input:
        parser.print_help()
        sys.exit(1)

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"[!] Error: Path does not exist: {input_path}")
        sys.exit(1)

    # Determine default output dir
    output_dir = args.output
    if not output_dir:
        if "inbox" in str(input_path).lower():
            output_dir = "client_outbox"
        else:
            output_dir = "outputs"

    os.makedirs(output_dir, exist_ok=True)

    if input_path.is_dir():
        files = [
            p for p in input_path.iterdir()
            if p.suffix.lower() in SUPPORTED_EXTS
            and not p.name.startswith("~")
            and not p.name.startswith(".")
        ]
        if not files:
            print(f"[*] No financial files found in directory {input_path}")
            return

        print(f"[*] Batch processing {len(files)} files from {input_path} -> {output_dir}")
        success_count = 0
        for f in files:
            try:
                process_file(str(f), output_dir=output_dir, scenarios=args.scenarios, n_years=args.n_years)
                success_count += 1
            except Exception as e:
                print(f"[!] Error processing {f.name}: {e}")

        print(f"\n[OK] Batch complete: {success_count}/{len(files)} packs compiled successfully in '{output_dir}'.")
    else:
        pack_res = process_file(str(input_path), output_dir=output_dir, scenarios=args.scenarios, n_years=args.n_years)
        print(f"\n[OK] Successfully compiled financial valuation pack: {pack_res['zip_path']}")


if __name__ == "__main__":
    main()
