"""
End-to-end integration tests for CLI pipeline and artifact generation.
"""

from pathlib import Path
import subprocess
import sys

from financial_engine.cli import run_pipeline


def test_package_cli_entrypoint_displays_help():
    project_root = Path(__file__).parent.parent
    result = subprocess.run(
        [sys.executable, "-m", "financial_engine", "--help"],
        capture_output=True,
        text=True,
        cwd=project_root,
        check=False,
    )

    assert result.returncode == 0
    assert "Automated Financial Modeling & Valuation Engine" in result.stdout


def test_cli_pipeline_execution(tmp_path):
    output_dir = tmp_path / "artifacts"
    model = run_pipeline(
        template="kaveri_foods",
        output_dir=str(output_dir),
        mc_iterations=500,
        export_excel=True,
        export_html=True,
        export_memo=True,
        export_json=True,
        quiet=True,
    )

    assert model.is_balanced
    assert round(model.value_per_share) == 252

    # Check generated files
    assert (output_dir / "kaveri_dashboard.html").exists()
    assert (output_dir / "kaveri_investment_memo.md").exists()
    assert (output_dir / "kaveri_valuation_output.json").exists()
    assert (output_dir / "kaveri_audit_certificate.json").exists()
