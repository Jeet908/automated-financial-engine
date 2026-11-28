import sys
sys.path.insert(0, 'C:/Users/HP/Downloads/Finance')
from src.engine.orchestrator import ModelOrchestrator

hist = {
    'revenue': [1000.0, 1120.0, 1243.2],
    'cogs': [585.0, 649.6, 716.1],
    'depreciation': [38.0, 40.0, 43.0],
    'interest': [28.4, 25.7, 23.0],
    'tax': [31.9, 40.4, 48.5],
    'cash': [222.8, 239.8, 269.5],
    'receivables': [123.3, 138.1, 153.3],
    'inventory': [80.1, 89.0, 98.1],
    'net_fixed_assets': [400.0, 430.0, 465.0],
    'payables': [96.2, 106.8, 117.7],
    'debt': [300.0, 270.0, 240.0],
    'share_capital': [50.0, 50.0, 50.0],
    'retained_earnings': [380.0, 470.1, 578.2],
}

orch = ModelOrchestrator()
result = orch.run(hist, scenarios=['Base', 'Bull', 'Bear'], n_years=5)

for sc, v in result.items():
    mo = v['model_output']
    bs_ok = all(abs(a - le) < 1e-6 for a, le in zip(mo.bs_total_assets, mo.bs_total_liab_equity))
    ev = v['dcf_results']['enterprise_value']
    irr = v['dcf_results']['irr'] * 100
    print(f"{sc}: EV={ev:.1f}  BS_balances={bs_ok}  IRR={irr:.1f}%")

print('SMOKE TEST PASSED')
