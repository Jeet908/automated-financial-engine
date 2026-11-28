"""
src/ingestion/market_universe.py — Autonomous Global Market Universe & Top 100 Benchmark Champions Directory.

Maintains the authoritative Top 100 Global Equities Universe categorized across the
11 Global Industry Classification Standard (GICS) sectors.
Provides autonomous market cap sorting, periodic sync, disk caching, and real-time typeahead query.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
INPUTS_DIR = PROJECT_ROOT / "inputs"
UNIVERSE_CACHE_PATH = INPUTS_DIR / "top100_universe.json"

# -------------------------------------------------------------------------
# The 11 Standard Global Industry Classification Standard (GICS) Sectors
# -------------------------------------------------------------------------
GICS_SECTORS: List[Dict[str, Any]] = [
    {
        "id": "information-technology",
        "name": "Information Technology",
        "slug": "technology",
        "display_name": "Information Technology (Semiconductors, Software & Cloud)",
        "icon": "⚡",
        "primary_benchmarks": ["NVDA", "AAPL", "MSFT", "TSM", "AVGO", "ASML", "TCS.NS"],
    },
    {
        "id": "financials",
        "name": "Financials",
        "slug": "financials",
        "display_name": "Financials (Global Banking, Insurance & Capital Markets)",
        "icon": "🏛️",
        "primary_benchmarks": ["JPM", "V", "MA", "BAC", "HDFCBANK.NS", "ICICIBANK.NS", "HSBC"],
    },
    {
        "id": "health-care",
        "name": "Health Care",
        "slug": "healthcare",
        "display_name": "Health Care (BioPharma, MedTech & Therapeutics)",
        "icon": "🧬",
        "primary_benchmarks": ["LLY", "NVO", "UNH", "JNJ", "ABBV", "AZN", "SUNPHARMA.NS"],
    },
    {
        "id": "consumer-discretionary",
        "name": "Consumer Discretionary",
        "slug": "consumer-discretionary",
        "display_name": "Consumer Discretionary (E-Commerce, Automotive & Luxury)",
        "icon": "🛍️",
        "primary_benchmarks": ["AMZN", "TSLA", "HD", "BABA", "TM", "MC.PA", "MARUTI.NS"],
    },
    {
        "id": "communication-services",
        "name": "Communication Services",
        "slug": "communication-services",
        "display_name": "Communication Services (Interactive Media & Telecom)",
        "icon": "📡",
        "primary_benchmarks": ["GOOGL", "META", "NFLX", "DIS", "BHARTIARTL.NS", "TMUS"],
    },
    {
        "id": "industrials",
        "name": "Industrials",
        "slug": "industrials",
        "display_name": "Industrials (Aerospace, Defence, Machinery & Logistics)",
        "icon": "⚙️",
        "primary_benchmarks": ["CAT", "GE", "RTX", "BA", "BEL.NS", "HAL.NS", "LT.NS"],
    },
    {
        "id": "consumer-staples",
        "name": "Consumer Staples",
        "slug": "consumer-staples",
        "display_name": "Consumer Staples (FMCG, Food & Retail)",
        "icon": "🛒",
        "primary_benchmarks": ["WMT", "PG", "COST", "KO", "PEP", "NESN.SW", "ITC.NS", "HINDUNILVR.NS"],
    },
    {
        "id": "energy",
        "name": "Energy",
        "slug": "energy",
        "display_name": "Energy (Oil, Gas & Clean Energy Transition)",
        "icon": "🛢️",
        "primary_benchmarks": ["XOM", "CVX", "SHEL", "TTE", "RELIANCE.NS", "BP"],
    },
    {
        "id": "materials",
        "name": "Materials",
        "slug": "materials",
        "display_name": "Materials (Specialty Chemicals, Mining & Metals)",
        "icon": "⛏️",
        "primary_benchmarks": ["LIN", "BHP", "RIO", "SHW", "TATASTEEL.NS"],
    },
    {
        "id": "utilities",
        "name": "Utilities",
        "slug": "utilities",
        "display_name": "Utilities (Power, Water & Renewable Infrastructure)",
        "icon": "💡",
        "primary_benchmarks": ["NEE", "SO", "DUK", "NTPC.NS", "POWERGRID.NS"],
    },
    {
        "id": "real-estate",
        "name": "Real Estate",
        "slug": "real-estate",
        "display_name": "Real Estate (REITs, Commercial & Digital Infrastructure)",
        "icon": "🏢",
        "primary_benchmarks": ["PLD", "AMT", "EQIX", "SPG", "DLF.NS"],
    },
]

# -------------------------------------------------------------------------
# Authoritative Seed Catalog of Top 100 Global Market Champions
# Ranked by Live Market Capitalization (USD Billions)
# -------------------------------------------------------------------------
SEED_TOP_100_CHAMPIONS: List[Dict[str, Any]] = [
    # Top Mega-Caps (1-10)
    {"ticker": "NVDA", "name": "NVIDIA Corporation", "sector": "Information Technology", "sub_industry": "Semiconductors", "market_cap_usd": 3520.0, "exchange": "NASDAQ", "country": "US", "currency": "USD"},
    {"ticker": "AAPL", "name": "Apple Inc.", "sector": "Information Technology", "sub_industry": "Consumer Electronics", "market_cap_usd": 3450.0, "exchange": "NASDAQ", "country": "US", "currency": "USD"},
    {"ticker": "MSFT", "name": "Microsoft Corporation", "sector": "Information Technology", "sub_industry": "Systems Software & Cloud", "market_cap_usd": 3150.0, "exchange": "NASDAQ", "country": "US", "currency": "USD"},
    {"ticker": "AMZN", "name": "Amazon.com Inc.", "sector": "Consumer Discretionary", "sub_industry": "Broadline Retail & Cloud", "market_cap_usd": 2180.0, "exchange": "NASDAQ", "country": "US", "currency": "USD"},
    {"ticker": "GOOGL", "name": "Alphabet Inc.", "sector": "Communication Services", "sub_industry": "Interactive Media & Services", "market_cap_usd": 2120.0, "exchange": "NASDAQ", "country": "US", "currency": "USD"},
    {"ticker": "META", "name": "Meta Platforms Inc.", "sector": "Communication Services", "sub_industry": "Interactive Media & AI", "market_cap_usd": 1480.0, "exchange": "NASDAQ", "country": "US", "currency": "USD"},
    {"ticker": "BRK-A", "name": "Berkshire Hathaway Inc.", "sector": "Financials", "sub_industry": "Multi-Sector Holdings & Insurance", "market_cap_usd": 1020.0, "exchange": "NYSE", "country": "US", "currency": "USD"},
    {"ticker": "TSM", "name": "Taiwan Semiconductor Manufacturing", "sector": "Information Technology", "sub_industry": "Semiconductors Foundry", "market_cap_usd": 990.0, "exchange": "NYSE", "country": "Taiwan", "currency": "USD"},
    {"ticker": "AVGO", "name": "Broadcom Inc.", "sector": "Information Technology", "sub_industry": "Semiconductors & Infrastructure", "market_cap_usd": 810.0, "exchange": "NASDAQ", "country": "US", "currency": "USD"},
    {"ticker": "TSLA", "name": "Tesla Inc.", "sector": "Consumer Discretionary", "sub_industry": "Automobile Manufacturers", "market_cap_usd": 790.0, "exchange": "NASDAQ", "country": "US", "currency": "USD"},

    # 11-25
    {"ticker": "LLY", "name": "Eli Lilly and Company", "sector": "Health Care", "sub_industry": "Pharmaceuticals", "market_cap_usd": 780.0, "exchange": "NYSE", "country": "US", "currency": "USD"},
    {"ticker": "JPM", "name": "JPMorgan Chase & Co.", "sector": "Financials", "sub_industry": "Diversified Banking", "market_cap_usd": 680.0, "exchange": "NYSE", "country": "US", "currency": "USD"},
    {"ticker": "WMT", "name": "Walmart Inc.", "sector": "Consumer Staples", "sub_industry": "Consumer Staples Merchandise", "market_cap_usd": 670.0, "exchange": "NYSE", "country": "US", "currency": "USD"},
    {"ticker": "V", "name": "Visa Inc.", "sector": "Financials", "sub_industry": "Transaction & Payment Processing", "market_cap_usd": 610.0, "exchange": "NYSE", "country": "US", "currency": "USD"},
    {"ticker": "NVO", "name": "Novo Nordisk A/S", "sector": "Health Care", "sub_industry": "Pharmaceuticals", "market_cap_usd": 590.0, "exchange": "NYSE", "country": "Denmark", "currency": "USD"},
    {"ticker": "XOM", "name": "Exxon Mobil Corporation", "sector": "Energy", "sub_industry": "Integrated Oil & Gas", "market_cap_usd": 520.0, "exchange": "NYSE", "country": "US", "currency": "USD"},
    {"ticker": "MA", "name": "Mastercard Incorporated", "sector": "Financials", "sub_industry": "Payment Processing", "market_cap_usd": 480.0, "exchange": "NYSE", "country": "US", "currency": "USD"},
    {"ticker": "UNH", "name": "UnitedHealth Group Incorporated", "sector": "Health Care", "sub_industry": "Managed Health Care", "market_cap_usd": 470.0, "exchange": "NYSE", "country": "US", "currency": "USD"},
    {"ticker": "ORCL", "name": "Oracle Corporation", "sector": "Information Technology", "sub_industry": "Application & Database Software", "market_cap_usd": 460.0, "exchange": "NYSE", "country": "US", "currency": "USD"},
    {"ticker": "COST", "name": "Costco Wholesale Corporation", "sector": "Consumer Staples", "sub_industry": "Merchandise Retail", "market_cap_usd": 415.0, "exchange": "NASDAQ", "country": "US", "currency": "USD"},
    {"ticker": "HD", "name": "The Home Depot Inc.", "sector": "Consumer Discretionary", "sub_industry": "Home Improvement Retail", "market_cap_usd": 410.0, "exchange": "NYSE", "country": "US", "currency": "USD"},
    {"ticker": "PG", "name": "Procter & Gamble Company", "sector": "Consumer Staples", "sub_industry": "Household Products", "market_cap_usd": 395.0, "exchange": "NYSE", "country": "US", "currency": "USD"},
    {"ticker": "BAC", "name": "Bank of America Corporation", "sector": "Financials", "sub_industry": "Diversified Banking", "market_cap_usd": 365.0, "exchange": "NYSE", "country": "US", "currency": "USD"},
    {"ticker": "ASML", "name": "ASML Holding N.V.", "sector": "Information Technology", "sub_industry": "Semiconductor Equipment", "market_cap_usd": 360.0, "exchange": "NASDAQ", "country": "Netherlands", "currency": "USD"},
    {"ticker": "NFLX", "name": "Netflix Inc.", "sector": "Communication Services", "sub_industry": "Movies & Entertainment", "market_cap_usd": 355.0, "exchange": "NASDAQ", "country": "US", "currency": "USD"},

    # 26-40
    {"ticker": "CRM", "name": "Salesforce Inc.", "sector": "Information Technology", "sub_industry": "Enterprise Cloud Software", "market_cap_usd": 340.0, "exchange": "NYSE", "country": "US", "currency": "USD"},
    {"ticker": "ABBV", "name": "AbbVie Inc.", "sector": "Health Care", "sub_industry": "Biotechnology", "market_cap_usd": 330.0, "exchange": "NYSE", "country": "US", "currency": "USD"},
    {"ticker": "KO", "name": "The Coca-Cola Company", "sector": "Consumer Staples", "sub_industry": "Non-Alcoholic Beverages", "market_cap_usd": 305.0, "exchange": "NYSE", "country": "US", "currency": "USD"},
    {"ticker": "SAP", "name": "SAP SE", "sector": "Information Technology", "sub_industry": "Application Software", "market_cap_usd": 295.0, "exchange": "NYSE", "country": "Germany", "currency": "USD"},
    {"ticker": "CVX", "name": "Chevron Corporation", "sector": "Energy", "sub_industry": "Integrated Oil & Gas", "market_cap_usd": 290.0, "exchange": "NYSE", "country": "US", "currency": "USD"},
    {"ticker": "LIN", "name": "Linde plc", "sector": "Materials", "sub_industry": "Industrial Gases", "market_cap_usd": 285.0, "exchange": "NYSE", "country": "US", "currency": "USD"},
    {"ticker": "AMD", "name": "Advanced Micro Devices Inc.", "sector": "Information Technology", "sub_industry": "Semiconductors", "market_cap_usd": 260.0, "exchange": "NASDAQ", "country": "US", "currency": "USD"},
    {"ticker": "PEP", "name": "PepsiCo Inc.", "sector": "Consumer Staples", "sub_industry": "Soft Drinks & Food", "market_cap_usd": 255.0, "exchange": "NASDAQ", "country": "US", "currency": "USD"},
    {"ticker": "TMO", "name": "Thermo Fisher Scientific Inc.", "sector": "Health Care", "sub_industry": "Life Sciences Tools", "market_cap_usd": 240.0, "exchange": "NYSE", "country": "US", "currency": "USD"},
    {"ticker": "RELIANCE.NS", "name": "Reliance Industries Limited", "sector": "Energy", "sub_industry": "Oil, Refining & Telecom", "market_cap_usd": 238.0, "exchange": "NSE", "country": "India", "currency": "INR"},
    {"ticker": "TM", "name": "Toyota Motor Corporation", "sector": "Consumer Discretionary", "sub_industry": "Automotive", "market_cap_usd": 235.0, "exchange": "NYSE", "country": "Japan", "currency": "USD"},
    {"ticker": "BABA", "name": "Alibaba Group Holding Limited", "sector": "Consumer Discretionary", "sub_industry": "Broadline Retail & Cloud", "market_cap_usd": 230.0, "exchange": "NYSE", "country": "China", "currency": "USD"},
    {"ticker": "QCOM", "name": "Qualcomm Incorporated", "sector": "Information Technology", "sub_industry": "Wireless Silicon", "market_cap_usd": 225.0, "exchange": "NASDAQ", "country": "US", "currency": "USD"},
    {"ticker": "CSCO", "name": "Cisco Systems Inc.", "sector": "Information Technology", "sub_industry": "Communications Equipment", "market_cap_usd": 220.0, "exchange": "NASDAQ", "country": "US", "currency": "USD"},
    {"ticker": "SHEL", "name": "Shell plc", "sector": "Energy", "sub_industry": "Integrated Oil & Gas", "market_cap_usd": 218.0, "exchange": "LSE", "country": "United Kingdom", "currency": "GBP"},

    # 41-55
    {"ticker": "AZN", "name": "AstraZeneca PLC", "sector": "Health Care", "sub_industry": "Biopharmaceuticals", "market_cap_usd": 215.0, "exchange": "LSE", "country": "United Kingdom", "currency": "GBP"},
    {"ticker": "MRK", "name": "Merck & Co. Inc.", "sector": "Health Care", "sub_industry": "Pharmaceuticals", "market_cap_usd": 210.0, "exchange": "NYSE", "country": "US", "currency": "USD"},
    {"ticker": "WFC", "name": "Wells Fargo & Company", "sector": "Financials", "sub_industry": "Diversified Banking", "market_cap_usd": 208.0, "exchange": "NYSE", "country": "US", "currency": "USD"},
    {"ticker": "TXN", "name": "Texas Instruments Incorporated", "sector": "Information Technology", "sub_industry": "Analog Semiconductors", "market_cap_usd": 205.0, "exchange": "NASDAQ", "country": "US", "currency": "USD"},
    {"ticker": "GE", "name": "GE Aerospace", "sector": "Industrials", "sub_industry": "Aerospace & Defence Propulsion", "market_cap_usd": 202.0, "exchange": "NYSE", "country": "US", "currency": "USD"},
    {"ticker": "CAT", "name": "Caterpillar Inc.", "sector": "Industrials", "sub_industry": "Construction & Mining Machinery", "market_cap_usd": 198.0, "exchange": "NYSE", "country": "US", "currency": "USD"},
    {"ticker": "IBM", "name": "International Business Machines", "sector": "Information Technology", "sub_industry": "IT Services & Hybrid Cloud", "market_cap_usd": 195.0, "exchange": "NYSE", "country": "US", "currency": "USD"},
    {"ticker": "PM", "name": "Philip Morris International Inc.", "sector": "Consumer Staples", "sub_industry": "Tobacco & Smoke-Free", "market_cap_usd": 192.0, "exchange": "NYSE", "country": "US", "currency": "USD"},
    {"ticker": "TCS.NS", "name": "Tata Consultancy Services Limited", "sector": "Information Technology", "sub_industry": "IT Services & Digital Consulting", "market_cap_usd": 190.0, "exchange": "NSE", "country": "India", "currency": "INR"},
    {"ticker": "INTU", "name": "Intuit Inc.", "sector": "Information Technology", "sub_industry": "Financial Software", "market_cap_usd": 185.0, "exchange": "NASDAQ", "country": "US", "currency": "USD"},
    {"ticker": "AMAT", "name": "Applied Materials Inc.", "sector": "Information Technology", "sub_industry": "Semiconductor Equipment", "market_cap_usd": 182.0, "exchange": "NASDAQ", "country": "US", "currency": "USD"},
    {"ticker": "NOW", "name": "ServiceNow Inc.", "sector": "Information Technology", "sub_industry": "Enterprise Cloud Workflow", "market_cap_usd": 180.0, "exchange": "NYSE", "country": "US", "currency": "USD"},
    {"ticker": "MS", "name": "Morgan Stanley", "sector": "Financials", "sub_industry": "Investment Banking & Wealth", "market_cap_usd": 178.0, "exchange": "NYSE", "country": "US", "currency": "USD"},
    {"ticker": "AXP", "name": "American Express Company", "sector": "Financials", "sub_industry": "Consumer Finance", "market_cap_usd": 175.0, "exchange": "NYSE", "country": "US", "currency": "USD"},
    {"ticker": "DIS", "name": "The Walt Disney Company", "sector": "Communication Services", "sub_industry": "Entertainment & Theme Parks", "market_cap_usd": 172.0, "exchange": "NYSE", "country": "US", "currency": "USD"},

    # 56-70
    {"ticker": "HDFCBANK.NS", "name": "HDFC Bank Limited", "sector": "Financials", "sub_industry": "Commercial Banking", "market_cap_usd": 168.0, "exchange": "NSE", "country": "India", "currency": "INR"},
    {"ticker": "GS", "name": "The Goldman Sachs Group Inc.", "sector": "Financials", "sub_industry": "Investment Banking", "market_cap_usd": 165.0, "exchange": "NYSE", "country": "US", "currency": "USD"},
    {"ticker": "RTX", "name": "RTX Corporation", "sector": "Industrials", "sub_industry": "Aerospace & Defence Systems", "market_cap_usd": 162.0, "exchange": "NYSE", "country": "US", "currency": "USD"},
    {"ticker": "UBER", "name": "Uber Technologies Inc.", "sector": "Industrials", "sub_industry": "Passenger Ground Transportation", "market_cap_usd": 160.0, "exchange": "NYSE", "country": "US", "currency": "USD"},
    {"ticker": "ISRG", "name": "Intuitive Surgical Inc.", "sector": "Health Care", "sub_industry": "Medical Equipment & Robotics", "market_cap_usd": 158.0, "exchange": "NASDAQ", "country": "US", "currency": "USD"},
    {"ticker": "BHARTIARTL.NS", "name": "Bharti Airtel Limited", "sector": "Communication Services", "sub_industry": "Telecommunications", "market_cap_usd": 155.0, "exchange": "NSE", "country": "India", "currency": "INR"},
    {"ticker": "HON", "name": "Honeywell International Inc.", "sector": "Industrials", "sub_industry": "Industrial Conglomerate", "market_cap_usd": 152.0, "exchange": "NASDAQ", "country": "US", "currency": "USD"},
    {"ticker": "PFE", "name": "Pfizer Inc.", "sector": "Health Care", "sub_industry": "Biopharmaceuticals", "market_cap_usd": 150.0, "exchange": "NYSE", "country": "US", "currency": "USD"},
    {"ticker": "BKNG", "name": "Booking Holdings Inc.", "sector": "Consumer Discretionary", "sub_industry": "Hotels & Travel Services", "market_cap_usd": 148.0, "exchange": "NASDAQ", "country": "US", "currency": "USD"},
    {"ticker": "TTE", "name": "TotalEnergies SE", "sector": "Energy", "sub_industry": "Integrated Energy", "market_cap_usd": 146.0, "exchange": "Euronext", "country": "France", "currency": "EUR"},
    {"ticker": "BHP", "name": "BHP Group Limited", "sector": "Materials", "sub_industry": "Diversified Metals & Mining", "market_cap_usd": 144.0, "exchange": "ASX", "country": "Australia", "currency": "USD"},
    {"ticker": "LRCX", "name": "Lam Research Corporation", "sector": "Information Technology", "sub_industry": "Semiconductor Equipment", "market_cap_usd": 142.0, "exchange": "NASDAQ", "country": "US", "currency": "USD"},
    {"ticker": "UNP", "name": "Union Pacific Corporation", "sector": "Industrials", "sub_industry": "Rail Transportation", "market_cap_usd": 140.0, "exchange": "NYSE", "country": "US", "currency": "USD"},
    {"ticker": "BLK", "name": "BlackRock Inc.", "sector": "Financials", "sub_industry": "Asset Management", "market_cap_usd": 138.0, "exchange": "NYSE", "country": "US", "currency": "USD"},
    {"ticker": "ICICIBANK.NS", "name": "ICICI Bank Limited", "sector": "Financials", "sub_industry": "Private Banking", "market_cap_usd": 135.0, "exchange": "NSE", "country": "India", "currency": "INR"},

    # 71-85
    {"ticker": "COP", "name": "ConocoPhillips", "sector": "Energy", "sub_industry": "Oil & Gas Exploration & Production", "market_cap_usd": 132.0, "exchange": "NYSE", "country": "US", "currency": "USD"},
    {"ticker": "NEE", "name": "NextEra Energy Inc.", "sector": "Utilities", "sub_industry": "Electric Utilities & Clean Power", "market_cap_usd": 130.0, "exchange": "NYSE", "country": "US", "currency": "USD"},
    {"ticker": "MC.PA", "name": "LVMH Moet Hennessy Louis Vuitton", "sector": "Consumer Discretionary", "sub_industry": "Luxury Goods", "market_cap_usd": 128.0, "exchange": "Euronext", "country": "France", "currency": "EUR"},
    {"ticker": "NESN.SW", "name": "Nestle S.A.", "sector": "Consumer Staples", "sub_industry": "Food & Nutrition", "market_cap_usd": 125.0, "exchange": "SIX", "country": "Switzerland", "currency": "CHF"},
    {"ticker": "INFY.NS", "name": "Infosys Limited", "sector": "Information Technology", "sub_industry": "IT Consulting & Services", "market_cap_usd": 122.0, "exchange": "NSE", "country": "India", "currency": "INR"},
    {"ticker": "BA", "name": "The Boeing Company", "sector": "Industrials", "sub_industry": "Aerospace & Commercial Aircraft", "market_cap_usd": 120.0, "exchange": "NYSE", "country": "US", "currency": "USD"},
    {"ticker": "PLD", "name": "Prologis Inc.", "sector": "Real Estate", "sub_industry": "Industrial REITs", "market_cap_usd": 118.0, "exchange": "NYSE", "country": "US", "currency": "USD"},
    {"ticker": "MCD", "name": "McDonald's Corporation", "sector": "Consumer Discretionary", "sub_industry": "Restaurants", "market_cap_usd": 115.0, "exchange": "NYSE", "country": "US", "currency": "USD"},
    {"ticker": "LOW", "name": "Lowe's Companies Inc.", "sector": "Consumer Discretionary", "sub_industry": "Home Improvement Retail", "market_cap_usd": 112.0, "exchange": "NYSE", "country": "US", "currency": "USD"},
    {"ticker": "SPGI", "name": "S&P Global Inc.", "sector": "Financials", "sub_industry": "Financial Data & Ratings", "market_cap_usd": 110.0, "exchange": "NYSE", "country": "US", "currency": "USD"},
    {"ticker": "SYK", "name": "Stryker Corporation", "sector": "Health Care", "sub_industry": "Medical Devices", "market_cap_usd": 108.0, "exchange": "NYSE", "country": "US", "currency": "USD"},
    {"ticker": "DE", "name": "Deere & Company", "sector": "Industrials", "sub_industry": "Agricultural Machinery", "market_cap_usd": 105.0, "exchange": "NYSE", "country": "US", "currency": "USD"},
    {"ticker": "SCHW", "name": "The Charles Schwab Corporation", "sector": "Financials", "sub_industry": "Brokerage & Custody", "market_cap_usd": 102.0, "exchange": "NYSE", "country": "US", "currency": "USD"},
    {"ticker": "LT.NS", "name": "Larsen & Toubro Limited", "sector": "Industrials", "sub_industry": "Infrastructure & EPC Engineering", "market_cap_usd": 100.0, "exchange": "NSE", "country": "India", "currency": "INR"},
    {"ticker": "ITC.NS", "name": "ITC Limited", "sector": "Consumer Staples", "sub_industry": "FMCG, Paper & Agri-Business", "market_cap_usd": 98.0, "exchange": "NSE", "country": "India", "currency": "INR"},

    # 86-100
    {"ticker": "HINDUNILVR.NS", "name": "Hindustan Unilever Limited", "sector": "Consumer Staples", "sub_industry": "Personal Care & Packaged Foods", "market_cap_usd": 95.0, "exchange": "NSE", "country": "India", "currency": "INR"},
    {"ticker": "AMT", "name": "American Tower Corporation", "sector": "Real Estate", "sub_industry": "Telecom Tower REITs", "market_cap_usd": 92.0, "exchange": "NYSE", "country": "US", "currency": "USD"},
    {"ticker": "EQIX", "name": "Equinix Inc.", "sector": "Real Estate", "sub_industry": "Data Center REITs", "market_cap_usd": 90.0, "exchange": "NASDAQ", "country": "US", "currency": "USD"},
    {"ticker": "SBIN.NS", "name": "State Bank of India", "sector": "Financials", "sub_industry": "Public Sector Banking", "market_cap_usd": 88.0, "exchange": "NSE", "country": "India", "currency": "INR"},
    {"ticker": "SO", "name": "The Southern Company", "sector": "Utilities", "sub_industry": "Regulated Electric Utilities", "market_cap_usd": 85.0, "exchange": "NYSE", "country": "US", "currency": "USD"},
    {"ticker": "DUK", "name": "Duke Energy Corporation", "sector": "Utilities", "sub_industry": "Electric & Gas Utilities", "market_cap_usd": 82.0, "exchange": "NYSE", "country": "US", "currency": "USD"},
    {"ticker": "RIO", "name": "Rio Tinto Group", "sector": "Materials", "sub_industry": "Metals & Mining", "market_cap_usd": 80.0, "exchange": "LSE", "country": "United Kingdom", "currency": "GBP"},
    {"ticker": "BEL.NS", "name": "Bharat Electronics Limited", "sector": "Industrials", "sub_industry": "Aerospace & Defence Electronics", "market_cap_usd": 78.0, "exchange": "NSE", "country": "India", "currency": "INR"},
    {"ticker": "HAL.NS", "name": "Hindustan Aeronautics Limited", "sector": "Industrials", "sub_industry": "Military Aviation & Defence", "market_cap_usd": 75.0, "exchange": "NSE", "country": "India", "currency": "INR"},
    {"ticker": "MARUTI.NS", "name": "Maruti Suzuki India Limited", "sector": "Consumer Discretionary", "sub_industry": "Passenger Vehicles", "market_cap_usd": 72.0, "exchange": "NSE", "country": "India", "currency": "INR"},
    {"ticker": "SUNPHARMA.NS", "name": "Sun Pharmaceutical Industries", "sector": "Health Care", "sub_industry": "Specialty & Generic Pharma", "market_cap_usd": 70.0, "exchange": "NSE", "country": "India", "currency": "INR"},
    {"ticker": "TATASTEEL.NS", "name": "Tata Steel Limited", "sector": "Materials", "sub_industry": "Steel Manufacturing", "market_cap_usd": 68.0, "exchange": "NSE", "country": "India", "currency": "INR"},
    {"ticker": "NTPC.NS", "name": "NTPC Limited", "sector": "Utilities", "sub_industry": "Power Generation & Renewables", "market_cap_usd": 65.0, "exchange": "NSE", "country": "India", "currency": "INR"},
    {"ticker": "POWERGRID.NS", "name": "Power Grid Corporation of India", "sector": "Utilities", "sub_industry": "Electric Power Transmission", "market_cap_usd": 62.0, "exchange": "NSE", "country": "India", "currency": "INR"},
    {"ticker": "DLF.NS", "name": "DLF Limited", "sector": "Real Estate", "sub_industry": "Commercial & Residential Real Estate", "market_cap_usd": 60.0, "exchange": "NSE", "country": "India", "currency": "INR"},
]

# Dynamic contender pool (#101-#122) so market-cap fluctuations rotate companies in & out of the Top 100
EXTRA_CONTENDER_CHAMPIONS: List[Dict[str, Any]] = [
    {"ticker": "ANET", "name": "Arista Networks Inc.", "sector": "Information Technology", "sub_industry": "Cloud Networking", "market_cap_usd": 59.0, "exchange": "NYSE", "country": "US", "currency": "USD"},
    {"ticker": "PANW", "name": "Palo Alto Networks Inc.", "sector": "Information Technology", "sub_industry": "Cybersecurity", "market_cap_usd": 58.5, "exchange": "NASDAQ", "country": "US", "currency": "USD"},
    {"ticker": "MU", "name": "Micron Technology Inc.", "sector": "Information Technology", "sub_industry": "Memory Semiconductors", "market_cap_usd": 58.0, "exchange": "NASDAQ", "country": "US", "currency": "USD"},
    {"ticker": "HCLTECH.NS", "name": "HCL Technologies Limited", "sector": "Information Technology", "sub_industry": "IT Services & Engineering", "market_cap_usd": 57.5, "exchange": "NSE", "country": "India", "currency": "INR"},
    {"ticker": "TMUS", "name": "T-Mobile US Inc.", "sector": "Communication Services", "sub_industry": "Wireless Telecom", "market_cap_usd": 57.0, "exchange": "NASDAQ", "country": "US", "currency": "USD"},
    {"ticker": "SONY", "name": "Sony Group Corporation", "sector": "Communication Services", "sub_industry": "Interactive Entertainment & Electronics", "market_cap_usd": 56.5, "exchange": "NYSE", "country": "Japan", "currency": "USD"},
    {"ticker": "C", "name": "Citigroup Inc.", "sector": "Financials", "sub_industry": "Global Banking", "market_cap_usd": 56.0, "exchange": "NYSE", "country": "US", "currency": "USD"},
    {"ticker": "BAJFINANCE.NS", "name": "Bajaj Finance Limited", "sector": "Financials", "sub_industry": "Consumer & SME Finance", "market_cap_usd": 55.5, "exchange": "NSE", "country": "India", "currency": "INR"},
    {"ticker": "CB", "name": "Chubb Limited", "sector": "Financials", "sub_industry": "Property & Casualty Insurance", "market_cap_usd": 55.0, "exchange": "NYSE", "country": "Switzerland", "currency": "USD"},
    {"ticker": "AMGN", "name": "Amgen Inc.", "sector": "Health Care", "sub_industry": "Biotechnology", "market_cap_usd": 54.5, "exchange": "NASDAQ", "country": "US", "currency": "USD"},
    {"ticker": "GILD", "name": "Gilead Sciences Inc.", "sector": "Health Care", "sub_industry": "Biopharmaceuticals", "market_cap_usd": 54.0, "exchange": "NASDAQ", "country": "US", "currency": "USD"},
    {"ticker": "TJX", "name": "The TJX Companies Inc.", "sector": "Consumer Discretionary", "sub_industry": "Apparel Retail", "market_cap_usd": 53.5, "exchange": "NYSE", "country": "US", "currency": "USD"},
    {"ticker": "TITAN.NS", "name": "Titan Company Limited", "sector": "Consumer Discretionary", "sub_industry": "Specialty Luxury & Watches", "market_cap_usd": 53.0, "exchange": "NSE", "country": "India", "currency": "INR"},
    {"ticker": "ETN", "name": "Eaton Corporation plc", "sector": "Industrials", "sub_industry": "Electrical Equipment", "market_cap_usd": 52.5, "exchange": "NYSE", "country": "US", "currency": "USD"},
    {"ticker": "BDL.NS", "name": "Bharat Dynamics Limited", "sector": "Industrials", "sub_industry": "Defence Missiles & Systems", "market_cap_usd": 52.0, "exchange": "NSE", "country": "India", "currency": "INR"},
    {"ticker": "CL", "name": "Colgate-Palmolive Company", "sector": "Consumer Staples", "sub_industry": "Household & Personal Products", "market_cap_usd": 51.5, "exchange": "NYSE", "country": "US", "currency": "USD"},
    {"ticker": "SLB", "name": "SLB (Schlumberger Limited)", "sector": "Energy", "sub_industry": "Oilfield Services & Equipment", "market_cap_usd": 51.0, "exchange": "NYSE", "country": "US", "currency": "USD"},
    {"ticker": "ONGC.NS", "name": "Oil and Natural Gas Corporation", "sector": "Energy", "sub_industry": "Oil & Gas Exploration", "market_cap_usd": 50.5, "exchange": "NSE", "country": "India", "currency": "INR"},
    {"ticker": "SHW", "name": "The Sherwin-Williams Company", "sector": "Materials", "sub_industry": "Specialty Chemicals & Coatings", "market_cap_usd": 50.0, "exchange": "NYSE", "country": "US", "currency": "USD"},
    {"ticker": "CEG", "name": "Constellation Energy Corporation", "sector": "Utilities", "sub_industry": "Nuclear & Clean Power", "market_cap_usd": 49.5, "exchange": "NASDAQ", "country": "US", "currency": "USD"},
    {"ticker": "SPG", "name": "Simon Property Group Inc.", "sector": "Real Estate", "sub_industry": "Retail REITs", "market_cap_usd": 49.0, "exchange": "NYSE", "country": "US", "currency": "USD"},
    {"ticker": "WELL", "name": "Welltower Inc.", "sector": "Real Estate", "sub_industry": "Health Care REITs", "market_cap_usd": 48.5, "exchange": "NYSE", "country": "US", "currency": "USD"},
]


class MarketUniverseManager:
    """
    Zero-touch manager that handles ranking, searching, filtering, and autonomous updates
    for the Top 100 global universe (dynamically sliced from a broader contender pool).
    """

    def __init__(self, cache_file: Path = UNIVERSE_CACHE_PATH):
        self.cache_file = cache_file
        self._universe: List[Dict[str, Any]] = []
        self._candidate_pool: List[Dict[str, Any]] = []
        self._last_synced_at: Optional[datetime] = None
        self._initialize_universe()

    def _initialize_universe(self) -> None:
        """Loads from disk cache or seeds from default champions + contender pool."""
        try:
            if self.cache_file.is_file():
                raw = json.loads(self.cache_file.read_text(encoding="utf-8"))
                if isinstance(raw, dict) and "champions" in raw:
                    pool = raw.get("candidate_pool") or raw["champions"]
                    if len(pool) > 100:
                        self._candidate_pool = pool
                        self._universe = raw["champions"][:100]
                        if "updated_at" in raw:
                            self._last_synced_at = datetime.fromisoformat(raw["updated_at"])
                        logger.info("Loaded %d global champions (pool=%d) from disk cache.", len(self._universe), len(self._candidate_pool))
                        return
        except Exception as exc:
            logger.warning("Could not read universe cache (%s). Re-seeding universe.", exc)

        # Fallback to seed catalog + contender pool
        self.recalculate_rankings(SEED_TOP_100_CHAMPIONS + EXTRA_CONTENDER_CHAMPIONS, persist=True)

    def recalculate_rankings(self, champions: List[Dict[str, Any]], persist: bool = True) -> List[Dict[str, Any]]:
        """
        Deduplicates, sorts the full contender pool by market cap descending,
        assigns ranks 1..N, and slices strictly to Top 100 for the active universe.
        """
        deduped: Dict[str, Dict[str, Any]] = {}
        for item in champions:
            ticker_key = str(item.get("ticker", "")).upper()
            if not ticker_key:
                continue
            existing = deduped.get(ticker_key)
            if existing is None or float(item.get("market_cap_usd", 0.0)) > float(existing.get("market_cap_usd", 0.0)):
                deduped[ticker_key] = dict(item)

        sorted_pool = sorted(
            deduped.values(),
            key=lambda x: float(x.get("market_cap_usd", 0.0)),
            reverse=True,
        )

        for idx, item in enumerate(sorted_pool, start=1):
            item["rank"] = idx

        self._candidate_pool = sorted_pool
        self._universe = sorted_pool[:100]
        self._last_synced_at = datetime.now(timezone.utc)

        if persist:
            try:
                self.cache_file.parent.mkdir(parents=True, exist_ok=True)
                payload = {
                    "updated_at": self._last_synced_at.isoformat(),
                    "total": len(self._universe),
                    "pool_total": len(self._candidate_pool),
                    "champions": self._universe,
                    "candidate_pool": self._candidate_pool,
                }
                self.cache_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
                logger.info("Successfully persisted Top %d champions (pool=%d) to %s", len(self._universe), len(self._candidate_pool), self.cache_file)
            except Exception as exc:
                logger.warning("Failed to persist universe cache: %s", exc)

        return self._universe

    def get_top_100(self, sector: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Returns the top champions, optionally filtered by GICS sector.
        """
        if not self._universe:
            self._initialize_universe()

        # If data is older than 24 hours, perform autonomous background sync check
        if self._last_synced_at:
            age_hours = (datetime.now(timezone.utc) - self._last_synced_at).total_seconds() / 3600.0
            if age_hours > 24.0:
                self.sync_market_data(force=False)

        results = self._universe
        if sector and sector.strip() and sector.strip().lower() not in {"all", "any", "all global sectors (top 100 benchmark champions)"}:
            sec_lower = sector.strip().lower()
            results = [c for c in results if sec_lower in c.get("sector", "").lower() or c.get("sector", "").lower() in sec_lower]

        return results[:limit]

    def search(self, query: str, sector: Optional[str] = None, limit: int = 12) -> List[Dict[str, Any]]:
        """
        Fast typeahead autocomplete search across ticker, company name, sub-industry, and country.
        """
        if not query or not query.strip():
            return self.get_top_100(sector=sector, limit=limit)

        q = query.strip().upper()
        candidates = self.get_top_100(sector=sector, limit=100)

        matches = []
        # Exact ticker match gets highest priority
        for c in candidates:
            if c["ticker"].upper() == q or c["ticker"].replace(".NS", "").upper() == q:
                matches.append(c)

        # Prefix ticker matches
        for c in candidates:
            if c not in matches and (c["ticker"].upper().startswith(q) or c["ticker"].replace(".NS", "").upper().startswith(q)):
                matches.append(c)

        # Name or sub-industry matches
        for c in candidates:
            if c not in matches and (q in c["name"].upper() or q in c.get("sub_industry", "").upper() or q in c.get("sector", "").upper()):
                matches.append(c)

        return matches[:limit]

    def sync_market_data(self, force: bool = False) -> Dict[str, Any]:
        """
        Autonomous synchronization pipeline:
        Polls live market capitalizations via yfinance when available, converts to USD billions,
        re-ranks the Top 100 universe, and updates the disk cache.
        Guaranteed zero crashes: if web network is down or rate-limited, safely retains last-known figures.
        """
        t0 = time.time()
        logger.info("Initiating autonomous market universe synchronization (force=%s)...", force)

        fx_to_usd = {
            "USD": 1.0,
            "INR": 1.0 / 84.0,
            "EUR": 1.06,
            "GBP": 1.26,
            "CHF": 1.13,
            "JPY": 1.0 / 152.0,
        }
        live_updated = 0
        yf_module = None
        try:
            import yfinance as yf_module  # type: ignore
        except Exception:
            yf_module = None

        updated_champions = []
        pool_source = self._candidate_pool or (SEED_TOP_100_CHAMPIONS + EXTRA_CONTENDER_CHAMPIONS)
        for item in pool_source:
            c = dict(item)
            if yf_module is not None:
                try:
                    fast = yf_module.Ticker(c["ticker"]).fast_info
                    raw_cap = fast.get("marketCap") if hasattr(fast, "get") else getattr(fast, "market_cap", None)
                    raw_curr = str((fast.get("currency") if hasattr(fast, "get") else getattr(fast, "currency", None)) or c.get("currency", "USD")).upper()
                    if raw_cap and float(raw_cap) > 0:
                        usd_cap_billions = (float(raw_cap) * fx_to_usd.get(raw_curr, 1.0)) / 1e9
                        if 1.0 <= usd_cap_billions <= 20000.0:
                            c["market_cap_usd"] = round(usd_cap_billions, 2)
                            live_updated += 1
                except Exception:
                    pass
            updated_champions.append(c)

        self.recalculate_rankings(updated_champions, persist=True)

        return {
            "status": "synchronized",
            "count": len(self._universe),
            "live_updated": live_updated,
            "updated_at": self._last_synced_at.isoformat() if self._last_synced_at else datetime.now(timezone.utc).isoformat(),
            "elapsed_ms": round((time.time() - t0) * 1000.0, 2),
        }

    def get_sectors(self) -> List[Dict[str, Any]]:
        """Returns GICS sectors annotated with the count of active top-100 champions."""
        counts: Dict[str, int] = {}
        for c in self._universe:
            sec = c.get("sector", "Other")
            counts[sec] = counts.get(sec, 0) + 1

        result = []
        for sec in GICS_SECTORS:
            entry = dict(sec)
            entry["champions_count"] = counts.get(sec["name"], 0)
            result.append(entry)
        return result


# Singleton instance
market_universe = MarketUniverseManager()
