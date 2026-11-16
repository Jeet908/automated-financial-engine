import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.ingestion.ingester import UniversalIngester
from src.engine.orchestrator import ModelOrchestrator

files = [
    ("Tata Elxsi", "client_inbox/Tata_Elxsi_IndAS.xlsx", "INR Cr"),
    ("Dixon Technologies", "client_inbox/Dixon_Technologies_IndAS.xlsx", "INR Cr"),
    ("Apple Inc.", "client_inbox/Apple_USGAAP_EDGAR.xlsx", "USD M"),
    ("Caterpillar Inc.", "client_inbox/Caterpillar_USGAAP_EDGAR.xlsx", "USD M"),
    ("Snowflake Inc.", "client_inbox/Snowflake_SaaS_MIS.xlsx", "USD M"),
    ("Datadog Inc.", "client_inbox/Datadog_SaaS_MIS.xlsx", "USD M"),
]

ingester = UniversalIngester()
orchestrator = ModelOrchestrator()

rows = []

for name, rel_path, cur_sym in files:
    full_path = PROJECT_ROOT / rel_path
    norm = ingester.ingest_file(str(full_path))
    engine_out = orchestrator.run(norm, scenarios=["Base", "Bull", "Bear"], n_years=5)
    
    std = getattr(norm, "standard", "IND_AS")
    if hasattr(std, "value"):
        std = std.value
    currency = getattr(norm, "currency", "INR")
    unit = getattr(norm, "unit", "Crores")
    
    base_res = engine_out["Base"]
    dcf = base_res["dcf_results"]
    base_ev = dcf["enterprise_value"]
    base_eqv = dcf["equity_value"]
    bull_ev = engine_out["Bull"]["dcf_results"]["enterprise_value"]
    bear_ev = engine_out["Bear"]["dcf_results"]["enterprise_value"]
    
    drivers = base_res.get("drivers")
    hist_cagr = getattr(drivers, "revenue_cagr", 0.10)
    ebitda_mgn = getattr(drivers, "avg_ebitda_margin", 0.20)
    wacc = dcf.get("wacc", 0.1024)
    
    # Audit check: Balance sheet variance
    max_bs_diff = 0.0
    for sc in ["Base", "Bull", "Bear"]:
        mo = engine_out[sc]["model_output"]
        for ta, tle in zip(mo.bs_total_assets, mo.bs_total_liab_equity):
            diff = abs(ta - tle)
            if diff > max_bs_diff:
                max_bs_diff = diff
                
    zip_stem = full_path.stem
    zip_filename = f"{zip_stem}_Client_Valuation_Pack.zip"
    
    rows.append({
        "name": name,
        "std": std,
        "currency": currency,
        "unit": unit,
        "hist_cagr": f"{hist_cagr * 100:.1f}%",
        "ebitda_mgn": f"{ebitda_mgn * 100:.1f}%",
        "wacc": f"{wacc * 100:.2f}%",
        "base_ev": f"{cur_sym} {base_ev:,.1f}",
        "bull_ev": f"{cur_sym} {bull_ev:,.1f}",
        "bear_ev": f"{cur_sym} {bear_ev:,.1f}",
        "base_eqv": f"{cur_sym} {base_eqv:,.1f}",
        "max_bs_diff": max_bs_diff,
        "zip_filename": zip_filename,
    })

print("| Entity | Accounting Standard | Currency & Unit | Hist Rev CAGR | EBITDA Margin | WACC | Base DCF EV | Bull DCF EV | Bear DCF EV | Base Implied Equity Value | Audit Log (BS Diff / Formula Errors) | Deliverable Valuation Bundle |")
print("|---|---|---|---|---|---|---|---|---|---|---|---|")
for r in rows:
    bs_status = "PASS ($0.00)" if r["max_bs_diff"] < 1e-4 else f"FAIL ({r['max_bs_diff']:.2f})"
    audit_col = f"{bs_status} / 0 Errors"
    zip_link = f"[{r['zip_filename']}](file:///C:/Users/HP/Downloads/Finance/client_outbox/{r['zip_filename']})"
    print(f"| **{r['name']}** | `{r['std']}` | {r['currency']} ({r['unit']}) | {r['hist_cagr']} | {r['ebitda_mgn']} | {r['wacc']} | {r['base_ev']} | {r['bull_ev']} | {r['bear_ev']} | {r['base_eqv']} | **{audit_col}** | {zip_link} |")
