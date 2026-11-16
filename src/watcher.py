"""
Automated File Watcher for the Financial Modeling & Valuation Engine.
Monitors the `inputs/` directory and auto-generates models into `outputs/`.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.cli import process_file

SUPPORTED_EXTENSIONS = {".xlsx", ".xls", ".csv", ".json", ".pdf"}


def run_watcher(
    watch_dir: str = "inputs",
    output_dir: str = "outputs",
    poll_interval: float = 2.0,
    run_once: bool = False,
):
    watch_path = Path(watch_dir)
    watch_path.mkdir(parents=True, exist_ok=True)
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    print(f"[*] Starting File Watcher on: {watch_path.resolve()}")
    print(f"[*] Generated models will be saved to: {out_path.resolve()}")
    print(f"[*] Polling interval: {poll_interval}s")

    processed_mtimes: dict[str, float] = {}

    while True:
        try:
            for item in watch_path.iterdir():
                if not item.is_file():
                    continue
                if item.suffix.lower() not in SUPPORTED_EXTENSIONS:
                    continue
                if item.name.startswith("~") or item.name.startswith("."):
                    continue

                mtime = item.stat().st_mtime
                last_mtime = processed_mtimes.get(str(item))

                if last_mtime is None or mtime > last_mtime:
                    print(f"\n[+] New/Updated file detected: {item.name}")
                    try:
                        saved = process_file(str(item), output_dir=output_dir)
                        processed_mtimes[str(item)] = mtime
                        zip_out = saved.get('zip_path', saved) if isinstance(saved, dict) else saved
                        print(f"[✓] Successfully generated valuation pack for {item.name} -> {zip_out}")
                    except Exception as e:
                        print(f"[!] Error processing {item.name}: {e}")
                        processed_mtimes[str(item)] = mtime

            if run_once:
                break
            time.sleep(poll_interval)
        except KeyboardInterrupt:
            print("\n[*] File watcher stopped by user.")
            break
        except Exception as e:
            print(f"[!] Watcher error: {e}")
            if run_once:
                break
            time.sleep(poll_interval)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Financial Engine File Watcher")
    parser.add_argument("--watch-dir", default="inputs", help="Directory to watch")
    parser.add_argument("--output-dir", default="outputs", help="Directory to output models")
    parser.add_argument("--once", action="store_true", help="Scan once and exit")
    parser.add_argument("--interval", type=float, default=2.0, help="Polling interval in seconds")
    args = parser.parse_args()

    run_watcher(args.watch_dir, args.output_dir, args.interval, run_once=args.once)
