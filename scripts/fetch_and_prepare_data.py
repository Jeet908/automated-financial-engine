"""
Real Public Company Data Fetcher & ERP Quirks Injection Suite.
Downloads authentic financials for Infosys (Ind AS, INR Crores) and Microsoft (US GAAP, USD Millions),
injects realistic client ERP quirks (merged banners, blank top rows, trailing footnotes,
mixed date headers, Tally/Zoho ledger names), and tests the pipeline.
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


def fetch_infosys_data() -> dict:
    """Fetch real multi-year financials for Infosys Ltd (INFY.NS) in INR Crores."""
    print("[*] Fetching real Infosys (INFY.NS) data from Yahoo Finance / NSE...")
    ticker = yf.Ticker("INFY.NS")
    fin = ticker.financials
    bs = ticker.balance_sheet
    cf = ticker.cashflow

    # Find common annual period dates (up to 4 years)
    common_dates = [c for c in fin.columns if c in bs.columns and c in cf.columns][:4]
    common_dates.sort()  # Chronological order

    periods = [f"FY{d.year % 100}A" for d in common_dates]
    date_strs = [d.strftime("%d-%b-%Y") for d in common_dates]

    # Helper to extract value safely and convert from INR to INR Crores (divide by 1e7)
    def get_val(df: pd.DataFrame, key: str, date, default=0.0) -> float:
        if key in df.index and date in df.columns:
            val = df.loc[key, date]
            if pd.notna(val):
                return round(float(val) / 1e7, 2)
        return default

    # Extract Income Statement
    rev = [get_val(fin, "Total Revenue", d) or get_val(fin, "Operating Revenue", d) for d in common_dates]
    cogs = [get_val(fin, "Cost Of Revenue", d) or get_val(fin, "Reconciled Cost Of Revenue", d) for d in common_dates]
    gross_profit = [get_val(fin, "Gross Profit", d, r - c) for d, r, c in zip(common_dates, rev, cogs)]
    ebitda = [get_val(fin, "EBITDA", d) or get_val(fin, "Normalized EBITDA", d) for d in common_dates]
    depr = [get_val(fin, "Reconciled Depreciation", d) for d in common_dates]
    ebit = [get_val(fin, "EBIT", d) or get_val(fin, "Operating Income", d) for d in common_dates]
    interest = [get_val(fin, "Interest Expense", d) for d in common_dates]
    pbt = [get_val(fin, "Pretax Income", d) for d in common_dates]
    tax = [get_val(fin, "Tax Provision", d) for d in common_dates]
    pat = [get_val(fin, "Net Income", d) or get_val(fin, "Net Income Common Stockholders", d) for d in common_dates]

    # Extract Balance Sheet
    cash = [get_val(bs, "Cash And Cash Equivalents", d) or get_val(bs, "Cash Cash Equivalents And Short Term Investments", d) for d in common_dates]
    recv = [get_val(bs, "Receivables", d) or get_val(bs, "Accounts Receivable", d) for d in common_dates]
    inv = [get_val(bs, "Inventory", d) for d in common_dates]
    nfa = [get_val(bs, "Net PPE", d) or get_val(bs, "Gross PPE", d) for d in common_dates]
    tot_assets = [get_val(bs, "Total Assets", d) for d in common_dates]
    # Other assets balancing
    other_assets = [round(ta - (c + r + i + nf), 2) for ta, c, r, i, nf in zip(tot_assets, cash, recv, inv, nfa)]

    payables = [get_val(bs, "Accounts Payable", d) or get_val(bs, "Payables", d) for d in common_dates]
    debt = [get_val(bs, "Total Debt", d) or get_val(bs, "Long Term Debt And Capital Lease Obligation", d) for d in common_dates]
    share_cap = [get_val(bs, "Common Stock", d) or get_val(bs, "Ordinary Shares Number", d, 50.0) for d in common_dates]
    # Ensure share cap is reasonable in crores
    share_cap = [sc if 10.0 <= sc <= 5000.0 else 2070.0 for sc in share_cap]
    re_earn = [get_val(bs, "Retained Earnings", d) for d in common_dates]
    tot_equity = [get_val(bs, "Stockholders Equity", d) or get_val(bs, "Common Stock Equity", d) for d in common_dates]
    tot_liab_eq = tot_assets  # Accounting identity

    other_liab = [round(ta - (p + d + te), 2) for ta, p, d, te in zip(tot_assets, payables, debt, tot_equity)]
    # Retained earnings adjustment so equity = share_capital + retained_earnings
    re_earn = [round(te - sc, 2) for te, sc in zip(tot_equity, share_cap)]

    # Extract Cash Flow
    cfo = [get_val(cf, "Operating Cash Flow", d) for d in common_dates]
    capex = [get_val(cf, "Capital Expenditure", d) for d in common_dates]
    capex = [abs(cx) for cx in capex]
    cfi = [get_val(cf, "Investing Cash Flow", d) for d in common_dates]
    cff = [get_val(cf, "Financing Cash Flow", d) for d in common_dates]
    divs = [abs(get_val(cf, "Common Stock Dividend Paid", d) or get_val(cf, "Cash Dividends Paid", d)) for d in common_dates]

    return {
        "metadata": {
            "name": "Infosys Limited",
            "standard": "IND_AS",
            "currency": "INR",
            "unit": "Crores",
            "fy_end_month": 3
        },
        "periods": periods,
        "date_strs": date_strs,
        "revenue": rev,
        "cogs": cogs,
        "gross_profit": gross_profit,
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
        "is_startup": False
    }


def fetch_microsoft_data() -> dict:
    """Fetch real multi-year financials for Microsoft Corp (MSFT) in USD Millions."""
    print("[*] Fetching real Microsoft (MSFT) data from Yahoo Finance / SEC EDGAR...")
    ticker = yf.Ticker("MSFT")
    fin = ticker.financials
    bs = ticker.balance_sheet
    cf = ticker.cashflow

    common_dates = [c for c in fin.columns if c in bs.columns and c in cf.columns][:4]
    common_dates.sort()

    periods = [f"FY{d.year % 100}A" for d in common_dates]
    date_strs = [d.strftime("%d-%b-%Y") for d in common_dates]

    def get_val(df: pd.DataFrame, key: str, date, default=0.0) -> float:
        if key in df.index and date in df.columns:
            val = df.loc[key, date]
            if pd.notna(val):
                return round(float(val) / 1e6, 2)
        return default

    rev = [get_val(fin, "Total Revenue", d) or get_val(fin, "Operating Revenue", d) for d in common_dates]
    cogs = [get_val(fin, "Cost Of Revenue", d) for d in common_dates]
    gross_profit = [get_val(fin, "Gross Profit", d, r - c) for d, r, c in zip(common_dates, rev, cogs)]
    ebitda = [get_val(fin, "EBITDA", d) or get_val(fin, "Normalized EBITDA", d) for d in common_dates]
    depr = [get_val(fin, "Reconciled Depreciation", d) for d in common_dates]
    ebit = [get_val(fin, "EBIT", d) or get_val(fin, "Operating Income", d) for d in common_dates]
    interest = [get_val(fin, "Interest Expense", d) for d in common_dates]
    pbt = [get_val(fin, "Pretax Income", d) for d in common_dates]
    tax = [get_val(fin, "Tax Provision", d) for d in common_dates]
    pat = [get_val(fin, "Net Income", d) for d in common_dates]

    cash = [get_val(bs, "Cash And Cash Equivalents", d) or get_val(bs, "Cash Cash Equivalents And Short Term Investments", d) for d in common_dates]
    recv = [get_val(bs, "Receivables", d) or get_val(bs, "Accounts Receivable", d) for d in common_dates]
    inv = [get_val(bs, "Inventory", d) for d in common_dates]
    nfa = [get_val(bs, "Net PPE", d) for d in common_dates]
    tot_assets = [get_val(bs, "Total Assets", d) for d in common_dates]
    other_assets = [round(ta - (c + r + i + nf), 2) for ta, c, r, i, nf in zip(tot_assets, cash, recv, inv, nfa)]

    payables = [get_val(bs, "Accounts Payable", d) for d in common_dates]
    debt = [get_val(bs, "Total Debt", d) or get_val(bs, "Long Term Debt And Capital Lease Obligation", d) for d in common_dates]
    share_cap = [get_val(bs, "Common Stock", d, 80000.0) for d in common_dates]
    tot_equity = [get_val(bs, "Stockholders Equity", d) for d in common_dates]
    tot_liab_eq = tot_assets
    other_liab = [round(ta - (p + d + te), 2) for ta, p, d, te in zip(tot_assets, payables, debt, tot_equity)]
    re_earn = [round(te - sc, 2) for te, sc in zip(tot_equity, share_cap)]

    cfo = [get_val(cf, "Operating Cash Flow", d) for d in common_dates]
    capex = [abs(get_val(cf, "Capital Expenditure", d)) for d in common_dates]
    cfi = [get_val(cf, "Investing Cash Flow", d) for d in common_dates]
    cff = [get_val(cf, "Financing Cash Flow", d) for d in common_dates]
    divs = [abs(get_val(cf, "Common Stock Dividend Paid", d)) for d in common_dates]

    return {
        "metadata": {
            "name": "Microsoft Corporation",
            "standard": "US_GAAP",
            "currency": "USD",
            "unit": "Millions",
            "fy_end_month": 6
        },
        "periods": periods,
        "date_strs": date_strs,
        "revenue": rev,
        "cogs": cogs,
        "gross_profit": gross_profit,
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
        "is_startup": False
    }


def write_clean_excel(data: dict, filepath: str):
    """Write standard clean Excel file."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Financial Statements"

    headers = ["Particulars"] + data["periods"]
    ws.append(headers)

    line_items = [
        ("Revenue", data["revenue"]),
        ("Cost of Goods Sold", data["cogs"]),
        ("Gross Profit", data["gross_profit"]),
        ("EBITDA", data["ebitda"]),
        ("Depreciation", data["depreciation"]),
        ("EBIT", data["ebit"]),
        ("Interest", data["interest"]),
        ("Profit Before Tax", data["pbt"]),
        ("Tax", data["tax"]),
        ("Profit After Tax", data["pat"]),
        ("Cash & Cash Equivalents", data["cash"]),
        ("Accounts Receivable", data["receivables"]),
        ("Inventory", data["inventory"]),
        ("Net Fixed Assets", data["net_fixed_assets"]),
        ("Other Assets", data["other_assets"]),
        ("Total Assets", data["total_assets"]),
        ("Accounts Payable", data["payables"]),
        ("Debt", data["debt"]),
        ("Other Liabilities", data["other_liabilities"]),
        ("Share Capital", data["share_capital"]),
        ("Retained Earnings", data["retained_earnings"]),
        ("Total Equity", data["total_equity"]),
        ("Total Liabilities & Equity", data["total_liab_equity"]),
        ("Cash Flow from Operations", data["cfo"]),
        ("Capital Expenditure", data["capex"]),
        ("Cash Flow from Investing", data["cfi"]),
        ("Cash Flow from Financing", data["cff"]),
        ("Dividends Paid", data["dividends"]),
    ]

    for label, vals in line_items:
        ws.append([label] + vals)

    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    wb.save(filepath)
    print(f"[✓] Saved clean Excel: {filepath}")


def write_quirky_excel(data: dict, filepath: str, erp_type: str = "Tally"):
    """
    Write quirky Excel workbook with realistic client ERP quirks:
    - 3 blank top rows
    - Merged title banner row
    - Mixed date formats in columns (e.g. 31-Mar-2024 vs FY23 vs 2022-03-31)
    - Custom Tally / Zoho ledger names
    - Trailing footnote rows
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"{erp_type} Export"

    # Row 1-3: Blank rows
    ws.append([])
    ws.append([])
    ws.append([])

    # Row 4: Merged Title Banner
    entity_name = data["metadata"]["name"]
    currency = data["metadata"]["currency"]
    unit = data["metadata"]["unit"]
    if erp_type == "Tally":
        banner_text = f"** {entity_name.upper()} - TALLY ERP 9 AUDITED STATEMENT (All amounts in {currency} {unit}) **"
    else:
        banner_text = f"## {entity_name.upper()} - ZOHO BOOKS LEDGER EXTRACT [CONFIDENTIAL - {currency} {unit}] ##"

    ws.append([banner_text])
    ws.merge_cells("A4:E4")
    banner_cell = ws["A4"]
    banner_cell.font = Font(bold=True, size=12, color="FFFFFF")
    banner_cell.fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    banner_cell.alignment = Alignment(horizontal="center")

    # Row 5: Blank separator
    ws.append([])

    # Row 6: Column Headers with Mixed Date Formats!
    # e.g., mix of "31-Mar-2024", "FY23", "2022-03-31", "31/03/2021"
    mixed_dates = []
    for i, d_str in enumerate(data.get("date_strs", data["periods"])):
        if i == 0:
            mixed_dates.append(f"31/03/{d_str[-4:]}" if "Mar" in d_str else f"30/06/{d_str[-4:]}")
        elif i == 1:
            mixed_dates.append(f"FY{d_str[-2:]}")
        elif i == 2:
            mixed_dates.append(f"{d_str[-4:]}-03-31" if "Mar" in d_str else f"{d_str[-4:]}-06-30")
        else:
            mixed_dates.append(d_str)

    header_label = "Ledger Accounts / Particulars" if erp_type == "Tally" else "Account Description / Line Item"
    ws.append([header_label] + mixed_dates)

    # Style header row
    header_row_idx = ws.max_row
    for cell in ws[header_row_idx]:
        cell.font = Font(bold=True)
        cell.fill = PatternFill(start_color="E2E8F0", end_color="E2E8F0", fill_type="solid")

    # Ledger mapping based on ERP
    if erp_type == "Tally":
        tally_items = [
            ("Revenue from Operations / Gross Turnover", data["revenue"]),
            ("Cost of Materials Consumed & Software Packages", data["cogs"]),
            ("Gross Profit / Margin", data["gross_profit"]),
            ("Operating Profit before Depreciation (EBITDA)", data["ebitda"]),
            ("Depreciation & Amortisation Expense", data["depreciation"]),
            ("Profit from Operations (EBIT)", data["ebit"]),
            ("Finance Costs / Interest on Borrowings", data["interest"]),
            ("Profit Before Exceptional Items & Tax", data["pbt"]),
            ("Tax Expense (Current & Deferred)", data["tax"]),
            ("Profit for the Period / PAT", data["pat"]),
            ("Cash & Bank Balances (Current Accounts)", data["cash"]),
            ("Trade Receivables Outstanding", data["receivables"]),
            ("Inventories / Stock-in-Trade", data["inventory"]),
            ("Property, Plant and Equipment (PPE)", data["net_fixed_assets"]),
            ("Other Non-Current & Current Assets", data["other_assets"]),
            ("Total Assets (Non-Current + Current)", data["total_assets"]),
            ("Trade Payables / Sundry Creditors", data["payables"]),
            ("Borrowings / Debt Obligations", data["debt"]),
            ("Other Financial & Current Liabilities", data["other_liabilities"]),
            ("Equity Share Capital (Fully Paid Up)", data["share_capital"]),
            ("Other Equity / Reserves and Surplus", data["retained_earnings"]),
            ("Total Equity / Shareholders' Funds", data["total_equity"]),
            ("Total Liabilities & Equity", data["total_liab_equity"]),
            ("Cash Flow from Operating Activities", data["cfo"]),
            ("Purchase of PPE & Capital Expenditure", data["capex"]),
            ("Cash Flow from Investing Activities", data["cfi"]),
            ("Cash Flow from Financing Activities", data["cff"]),
            ("Dividend Paid on Equity Shares", data["dividends"]),
        ]
        line_items = tally_items
    else:  # Zoho Books
        zoho_items = [
            ("Total Revenues / Net Sales", data["revenue"]),
            ("Cost of Goods Sold & Cost of Revenue", data["cogs"]),
            ("Gross Margin / Gross Profit", data["gross_profit"]),
            ("EBITDA (Earnings Before Interest, Tax, D&A)", data["ebitda"]),
            ("Depreciation and Amortization", data["depreciation"]),
            ("Operating Income (EBIT)", data["ebit"]),
            ("Interest Expense / Financing Fees", data["interest"]),
            ("Income Before Income Taxes (PBT)", data["pbt"]),
            ("Provision for Income Taxes", data["tax"]),
            ("Net Income / Profit After Tax", data["pat"]),
            ("Cash and Cash Equivalents", data["cash"]),
            ("Accounts Receivable, Net", data["receivables"]),
            ("Inventories", data["inventory"]),
            ("Property, Plant and Equipment, Net", data["net_fixed_assets"]),
            ("Other Assets & Intangibles", data["other_assets"]),
            ("Total Assets", data["total_assets"]),
            ("Accounts Payable & Trade Creditors", data["payables"]),
            ("Short-Term & Long-Term Debt Obligations", data["debt"]),
            ("Other Current & Non-Current Liabilities", data["other_liabilities"]),
            ("Common Stock / Paid-In Capital", data["share_capital"]),
            ("Retained Earnings & Reserves", data["retained_earnings"]),
            ("Total Stockholders' Equity", data["total_equity"]),
            ("Total Liabilities and Stockholders' Equity", data["total_liab_equity"]),
            ("Net Cash Provided by Operating Activities", data["cfo"]),
            ("Additions to PPE (Capital Expenditures)", data["capex"]),
            ("Net Cash Used in Investing Activities", data["cfi"]),
            ("Net Cash Used in Financing Activities", data["cff"]),
            ("Payments of Cash Dividends", data["dividends"]),
        ]
        line_items = zoho_items

    for label, vals in line_items:
        ws.append([label] + vals)

    # Trailing Footnote Rows
    ws.append([])
    if erp_type == "Tally":
        ws.append(["* Note 1: Figures in INR Crores. Subject to statutory audit reconciliation."])
        ws.append(["** Note 2: Previous period figures have been regrouped/reclassified where necessary."])
        ws.append(["--- END OF REPORT (Generated by TallyPrime v4.0 on 14-Nov-2026) ---"])
    else:
        ws.append(["* Note: Amounts in USD Millions. Source: Zoho Books ERP & SEC Form 10-K."])
        ws.append(["** Note: Non-GAAP figures adjusted for one-time impairment."])
        ws.append(["--- CONFIDENTIAL EXPORT (Generated by Zoho Books Automation) ---"])

    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    wb.save(filepath)
    print(f"[✓] Saved quirky {erp_type} Excel: {filepath}")


def main():
    print("=" * 70)
    print("AUTONOMOUS REAL-DATA STRESS TEST: INFOSYS (IND AS) & MICROSOFT (US GAAP)")
    print("=" * 70)

    # 1. Fetch real data
    infosys_data = fetch_infosys_data()
    microsoft_data = fetch_microsoft_data()

    # 2. Write clean Excel files
    clean_infy_path = "inputs/clean_infosys_ind_as.xlsx"
    clean_msft_path = "inputs/clean_microsoft_us_gaap.xlsx"
    write_clean_excel(infosys_data, clean_infy_path)
    write_clean_excel(microsoft_data, clean_msft_path)

    # 3. Write quirky ERP files
    quirky_infy_path = "inputs/quirky_infosys_tally_ind_as.xlsx"
    quirky_msft_path = "inputs/quirky_microsoft_zoho_us_gaap.xlsx"
    write_quirky_excel(infosys_data, quirky_infy_path, erp_type="Tally")
    write_quirky_excel(microsoft_data, quirky_msft_path, erp_type="Zoho")

    print("\n[+] All 4 Excel fixtures created successfully in inputs/")
    print(f"  1. {clean_infy_path}")
    print(f"  2. {clean_msft_path}")
    print(f"  3. {quirky_infy_path} (Quirky Tally ERP)")
    print(f"  4. {quirky_msft_path} (Quirky Zoho Books ERP)")


if __name__ == "__main__":
    main()
