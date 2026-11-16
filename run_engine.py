"""
One-Click Zero-Touch Execution Entrypoint.
Runs the complete Automated Financial Modeling & Valuation Engine pipeline.
"""

import sys
from pathlib import Path

# Add current workspace to sys.path
sys.path.insert(0, str(Path(__file__).parent))

from financial_engine.cli import run_pipeline


if __name__ == "__main__":
    print("[*] Launching 100% Zero-Touch Automated Financial Modeling & Valuation Engine...")
    model = run_pipeline(
        template="kaveri_foods",
        output_dir="artifacts",
        mc_iterations=10000,
        export_excel=True,
        export_html=True,
        export_memo=True,
        export_json=True,
    )
    print(f"[✓] Completed successfully. Implied Share Price: {model.config.metadata.currency.value} {model.value_per_share:.0f}")
