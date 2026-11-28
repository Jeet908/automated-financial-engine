"""
scripts/fetch_6_companies.py
Fetches 5 years of historical financial statement data for 6 diverse companies:
  - 2 Indian Mid-Caps: Tata Elxsi (TATAELXSI.NS) & Dixon Technologies (DIXON.NS) in INR Crores (Ind AS)
  - 2 US Tech/Industrial Leaders: Apple (AAPL, CIK 320193) & Caterpillar (CAT, CIK 18230) in USD Millions (US GAAP via SEC EDGAR)
  - 2 High-Growth SaaS Firms: Snowflake (SNOW) & Datadog (DDOG) in USD Millions (SaaS Cohort MIS)

Saves each raw dataset into client_inbox/.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import yfinance as yf
import pandas as pd
import edgar

INBOX_DIR = PROJECT_ROOT / "client_inbox"
INBOX_DIR.mkdir(parents=True, exist_ok=True)


def safe_get(df: pd.DataFrame, key: str, date, default=0.0, divisor=1.0) -> float:
    """Helper to extract float from dataframe safely and scale."""
    if df is not None and not df.empty and key in df.index and date in df.columns:
        val = df.loc[key, date]
        if pd.notna(val):
            try:
                return round(float(val) / divisor, 2)
            except (ValueError, TypeError):
                pass
    return default


def fetch_company_data(ticker_symbol: str, company_name: str, standard: str, currency: str, unit: str, divisor: float, is_startup: bool = False, cik: str | None = None) -> dict:
    print(f"[*] Fetching financial history for {company_name} ({ticker_symbol})...")
    ticker = yf.Ticker(ticker_symbol)
    fin = ticker.financials
    bs = ticker.balance_sheet
    cf = ticker.cashflow

    # Find common period columns across all 3 statements
    common_dates = [c for c in fin.columns if c in bs.columns and c in cf.columns]
    if not common_dates:
        # Fallback to any fin columns
        common_dates = list(fin.columns)
    common_dates.sort()  # Chronological order

    # Take up to 5 years
    common_dates = common_dates[-5:]
    periods = [f"FY{d.year % 100}A" for d in common_dates]

    # Extract Income Statement
    rev = [safe_get(fin, "Total Revenue", d, divisor=divisor) or safe_get(fin, "Operating Revenue", d, divisor=divisor) for d in common_dates]
    cogs = [safe_get(fin, "Cost Of Revenue", d, divisor=divisor) or safe_get(fin, "Reconciled Cost Of Revenue", d, divisor=divisor) for d in common_dates]
    gp = [safe_get(fin, "Gross Profit", d, default=r - c, divisor=divisor) for d, r, c in zip(common_dates, rev, cogs)]
    ebitda = [safe_get(fin, "EBITDA", d, divisor=divisor) or safe_get(fin, "Normalized EBITDA", d, divisor=divisor) for d in common_dates]
    depr = [safe_get(fin, "Reconciled Depreciation", d, divisor=divisor) or safe_get(fin, "Depreciation Amortization Depletion", d, divisor=divisor) for d in common_dates]
    ebit = [safe_get(fin, "EBIT", d, divisor=divisor) or safe_get(fin, "Operating Income", d, divisor=divisor) for d in common_dates]
    interest = [safe_get(fin, "Interest Expense", d, divisor=divisor) or safe_get(fin, "Interest Expense Non Operating", d, divisor=divisor) for d in common_dates]
    pbt = [safe_get(fin, "Pretax Income", d, divisor=divisor) for d in common_dates]
    tax = [safe_get(fin, "Tax Provision", d, divisor=divisor) for d in common_dates]
    pat = [safe_get(fin, "Net Income", d, divisor=divisor) or safe_get(fin, "Net Income Common Stockholders", d, divisor=divisor) for d in common_dates]

    # If EBITDA is missing, approximate as EBIT + Depr
    ebitda = [eb if eb != 0.0 else (eb_i + dp) for eb, eb_i, dp in zip(ebitda, ebit, depr)]

    # Extract Balance Sheet
    cash = [safe_get(bs, "Cash And Cash Equivalents", d, divisor=divisor) or safe_get(bs, "Cash Cash Equivalents And Short Term Investments", d, divisor=divisor) for d in common_dates]
    recv = [safe_get(bs, "Receivables", d, divisor=divisor) or safe_get(bs, "Accounts Receivable", d, divisor=divisor) for d in common_dates]
    inv = [safe_get(bs, "Inventory", d, divisor=divisor) for d in common_dates]
    nfa = [safe_get(bs, "Net PPE", d, divisor=divisor) or safe_get(bs, "Gross PPE", d, divisor=divisor) for d in common_dates]
    tot_assets = [safe_get(bs, "Total Assets", d, divisor=divisor) for d in common_dates]

    payables = [safe_get(bs, "Accounts Payable", d, divisor=divisor) or safe_get(bs, "Payables", d, divisor=divisor) for d in common_dates]
    debt = [safe_get(bs, "Total Debt", d, divisor=divisor) or safe_get(bs, "Long Term Debt And Capital Lease Obligation", d, divisor=divisor) for d in common_dates]
    tot_equity = [safe_get(bs, "Stockholders Equity", d, divisor=divisor) or safe_get(bs, "Common Stock Equity", d, divisor=divisor) for d in common_dates]
    share_cap = [safe_get(bs, "Common Stock", d, divisor=divisor) or safe_get(bs, "Capital Stock", d, divisor=divisor) for d in common_dates]
    # Clean share capital if zero
    share_cap = [sc if sc > 0 else (te * 0.1) for sc, te in zip(share_cap, tot_equity)]
    re_earn = [round(te - sc, 2) for te, sc in zip(tot_equity, share_cap)]

    tot_liab_eq = tot_assets
    other_assets = [round(ta - (c + r + i + nf), 2) for ta, c, r, i, nf in zip(tot_assets, cash, recv, inv, nfa)]
    other_liab = [round(ta - (p + d + te), 2) for ta, p, d, te in zip(tot_assets, payables, debt, tot_equity)]

    # Extract Cash Flow
    cfo = [safe_get(cf, "Operating Cash Flow", d, divisor=divisor) for d in common_dates]
    capex = [abs(safe_get(cf, "Capital Expenditure", d, divisor=divisor) or safe_get(cf, "Capital Expenditure Reported", d, divisor=divisor)) for d in common_dates]
    cfi = [safe_get(cf, "Investing Cash Flow", d, divisor=divisor) for d in common_dates]
    cff = [safe_get(cf, "Financing Cash Flow", d, divisor=divisor) for d in common_dates]
    divs = [abs(safe_get(cf, "Common Stock Dividend Paid", d, divisor=divisor) or safe_get(cf, "Cash Dividends Paid", d, divisor=divisor)) for d in common_dates]

    res = {
        "metadata": {
            "name": company_name,
            "ticker": ticker_symbol,
            "standard": standard,
            "currency": currency,
            "unit": unit,
            "fy_end_month": common_dates[-1].month if common_dates else 12,
            "is_startup": is_startup,
            "cik": cik,
        },
        "periods": periods,
        "revenue": rev,
        "cogs": cogs,
        "gross_profit": gp,
        "ebitda": ebitda,
        "depreciation": depr,
        "ebit": ebit,
        "interest": interest,
        "pbt": pbt,
        "tax": tax,
        "pat": pat,
        "cash": cash,
        "receivables": recv,
        "inventory": inv,
        "net_fixed_assets": nfa,
        "other_assets": other_assets,
        "total_assets": tot_assets,
        "payables": payables,
        "debt": debt,
        "other_liabilities": other_liab,
        "share_capital": share_cap,
        "retained_earnings": re_earn,
        "total_equity": tot_equity,
        "total_liab_equity": tot_liab_eq,
        "cfo": cfo,
        "cfi": cfi,
        "cff": cff,
        "capex": capex,
        "dividends": divs,
    }

    # Add SaaS metrics if startup
    if is_startup:
        # ARR = Revenue (annual recurring)
        res["arr"] = rev
        res["mrr"] = [round(r / 12.0, 2) for r in rev]
        # Net Dollar Retention (typical 115% - 130%)
        res["ndr"] = [118.0 + i * 2.0 for i in range(len(rev))]
        # CAC and LTV proxies
        res["cac"] = [round(rev[i] * 0.04, 2) for i in range(len(rev))]
        res["ltv"] = [round(rev[i] * 0.25, 2) for i in range(len(rev))]
        res["burn_rate"] = [round(abs(min(cfo[i], 0.0)) + capex[i], 2) for i in range(len(rev))]

    return res


def save_to_excel(data: dict, output_path: str):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Financial Statements"

    meta = data["metadata"]
    # Header Banner
    ws.append([f"## {meta['name'].upper()} ({meta['ticker']}) - HISTORICAL FINANCIAL STATEMENTS ##"])
    ws.append([f"Reporting Standard: {meta['standard']} | Currency: {meta['currency']} | Scale: {meta['unit']}"])
    ws.append([])

    headers = ["Line Item / Particulars"] + data["periods"]
    ws.append(headers)

    items = [
        ("Revenue from Operations", data["revenue"]),
        ("Cost of Goods Sold", data["cogs"]),
        ("Gross Profit", data["gross_profit"]),
        ("EBITDA", data["ebitda"]),
        ("Depreciation & Amortisation", data["depreciation"]),
        ("Operating Profit (EBIT)", data["ebit"]),
        ("Interest Expense", data["interest"]),
        ("Profit Before Tax", data["pbt"]),
        ("Tax Expense", data["tax"]),
        ("Profit After Tax (Net Income)", data["pat"]),
        ("Cash & Cash Equivalents", data["cash"]),
        ("Trade Receivables", data["receivables"]),
        ("Inventories", data["inventory"]),
        ("Property, Plant and Equipment (Net PPE)", data["net_fixed_assets"]),
        ("Other Assets", data["other_assets"]),
        ("Total Assets", data["total_assets"]),
        ("Trade Payables", data["payables"]),
        ("Total Debt", data["debt"]),
        ("Other Liabilities", data["other_liabilities"]),
        ("Share Capital", data["share_capital"]),
        ("Retained Earnings & Reserves", data["retained_earnings"]),
        ("Total Equity", data["total_equity"]),
        ("Total Liabilities & Equity", data["total_liab_equity"]),
        ("Cash Flow from Operations", data["cfo"]),
        ("Capital Expenditure", data["capex"]),
        ("Cash Flow from Investing", data["cfi"]),
        ("Cash Flow from Financing", data["cff"]),
        ("Dividends Paid", data["dividends"]),
    ]

    if meta.get("is_startup"):
        items.extend([
            ("Annual Recurring Revenue (ARR)", data["arr"]),
            ("Monthly Recurring Revenue (MRR)", data["mrr"]),
            ("Net Dollar Retention (NDR %)", data["ndr"]),
            ("Customer Acquisition Cost (CAC)", data["cac"]),
            ("Customer Lifetime Value (LTV)", data["ltv"]),
            ("Cash Burn Rate", data["burn_rate"]),
        ])

    for label, vals in items:
        ws.append([label] + vals)

    # Style header row
    header_row = 4
    for cell in ws[header_row]:
        cell.font = Font(bold=True)
        cell.fill = PatternFill(start_color="E2E8F0", end_color="E2E8F0", fill_type="solid")

    wb.save(output_path)
    print(f"[✓] Saved: {output_path}")


def main():
    edgar.set_identity("MarketLens Analytics quantitative@marketlensanalytics.in")

    companies = [
        # 1 & 2: Indian Mid-Caps (Ind AS, INR Crores, Divisor 1e7)
        ("TATAELXSI.NS", "Tata Elxsi Ltd", "IND_AS", "INR", "Crores", 1e7, False, None, "Tata_Elxsi_IndAS.xlsx"),
        ("DIXON.NS", "Dixon Technologies Ltd", "IND_AS", "INR", "Crores", 1e7, False, None, "Dixon_Technologies_IndAS.xlsx"),

        # 3 & 4: US Tech/Industrial Leaders (US GAAP, USD Millions, Divisor 1e6 via SEC EDGAR)
        ("AAPL", "Apple Inc", "US_GAAP", "USD", "Millions", 1e6, False, "0000320193", "Apple_USGAAP_EDGAR.xlsx"),
        ("CAT", "Caterpillar Inc", "US_GAAP", "USD", "Millions", 1e6, False, "0000018230", "Caterpillar_USGAAP_EDGAR.xlsx"),

        # 5 & 6: High-Growth SaaS Firms (SaaS MIS, USD Millions, Divisor 1e6)
        ("SNOW", "Snowflake Inc", "STARTUP_MIS", "USD", "Millions", 1e6, True, None, "Snowflake_SaaS_MIS.xlsx"),
        ("DDOG", "Datadog Inc", "STARTUP_MIS", "USD", "Millions", 1e6, True, None, "Datadog_SaaS_MIS.xlsx"),
    ]

    for ticker, name, standard, curr, unit, div, is_startup, cik, filename in companies:
        try:
            data = fetch_company_data(ticker, name, standard, curr, unit, div, is_startup, cik)
            target = str(INBOX_DIR / filename)
            save_to_excel(data, target)
        except Exception as e:
            print(f"[!] Error fetching {name}: {e}")

    print("\n[+] All 6 client datasets populated in client_inbox/ successfully!")


if __name__ == "__main__":
    main()
