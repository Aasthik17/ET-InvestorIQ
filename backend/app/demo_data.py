"""
ET InvestorIQ — Mock / Demo Data
Realistic January 2025 Indian market data used when MOCK_MODE=true or
when live API calls fail. Every function in data_service.py uses this as fallback.
"""

import random
import math
from datetime import datetime, timedelta

# ─── Helpers ──────────────────────────────────────────────────────────────────


def _sparkline(base: float, direction: int = 1, points: int = 20) -> list:
    """Generate a realistic-looking sparkline (% change from open)."""
    vals = [0.0]
    for _ in range(points - 1):
        step = random.gauss(0, 0.15) + direction * 0.04
        vals.append(round(vals[-1] + step, 3))
    return vals


def _ohlcv_series(start_price: float, days: int = 252,
                  trend: float = 0.0003, vol: float = 0.015) -> list:
    """Generate synthetic OHLCV data with realistic price action."""
    price = start_price
    rows = []
    base_date = datetime(2024, 3, 15)
    for i in range(days):
        dt = base_date + timedelta(days=i)
        # Skip weekends
        if dt.weekday() >= 5:
            continue
        daily_ret = random.gauss(trend, vol)
        open_  = round(price * (1 + random.gauss(0, 0.003)), 2)
        close  = round(open_ * (1 + daily_ret), 2)
        high   = round(max(open_, close) * (1 + abs(random.gauss(0, 0.005))), 2)
        low    = round(min(open_, close) * (1 - abs(random.gauss(0, 0.005))), 2)
        volume = int(random.gauss(5_000_000, 1_500_000) * (1 + abs(daily_ret) * 10))
        rows.append({
            "date": dt.strftime("%Y-%m-%d"),
            "open": open_, "high": high, "low": low, "close": close,
            "volume": max(100_000, volume),
        })
        price = close
    return rows


# ─── MOCK DATA ────────────────────────────────────────────────────────────────

MOCK_DATA = {

    # ── Index quotes ────────────────────────────────────────────────────────
    "index_quotes": {
        "nifty50": {
            "name": "NIFTY 50", "value": 23456.80, "change": 124.50,
            "change_pct": 0.53, "high": 23512.35, "low": 23380.10,
            "sparkline": _sparkline(23456, direction=1),
        },
        "sensex": {
            "name": "SENSEX", "value": 77145.20, "change": 415.30,
            "change_pct": 0.54, "high": 77290.00, "low": 76880.50,
            "sparkline": _sparkline(77145, direction=1),
        },
        "banknifty": {
            "name": "BANK NIFTY", "value": 49234.50, "change": -123.40,
            "change_pct": -0.25, "high": 49420.00, "low": 49110.00,
            "sparkline": _sparkline(49234, direction=-1),
        },
        "vix": {
            "name": "INDIA VIX", "value": 13.42, "change": 0.21,
            "change_pct": 1.59, "high": 13.88, "low": 13.15,
            "sparkline": _sparkline(13.42, direction=0),
        },
    },

    # ── Top movers ──────────────────────────────────────────────────────────
    "top_movers": {
        "gainers": [
            {"symbol": "HDFCBANK",  "company": "HDFC Bank Ltd",              "ltp": 1648.25, "change_pct": 3.12, "volume": 12_400_000},
            {"symbol": "WIPRO",     "company": "Wipro Ltd",                  "ltp": 487.50,  "change_pct": 2.87, "volume": 8_200_000},
            {"symbol": "ADANIENT",  "company": "Adani Enterprises Ltd",      "ltp": 2436.10, "change_pct": 2.54, "volume": 4_500_000},
            {"symbol": "BAJFINANCE","company": "Bajaj Finance Ltd",           "ltp": 6984.30, "change_pct": 2.31, "volume": 2_100_000},
            {"symbol": "TATAMOTORS","company": "Tata Motors Ltd",             "ltp": 876.45,  "change_pct": 2.18, "volume": 15_600_000},
            {"symbol": "SUNPHARMA", "company": "Sun Pharmaceutical Ind Ltd", "ltp": 1654.80, "change_pct": 1.95, "volume": 3_400_000},
            {"symbol": "LT",        "company": "Larsen & Toubro Ltd",        "ltp": 3547.20, "change_pct": 1.78, "volume": 2_800_000},
            {"symbol": "TITAN",     "company": "Titan Company Ltd",           "ltp": 3254.90, "change_pct": 1.62, "volume": 1_900_000},
            {"symbol": "NTPC",      "company": "NTPC Ltd",                   "ltp": 348.75,  "change_pct": 1.51, "volume": 22_100_000},
            {"symbol": "POWERGRID", "company": "Power Grid Corp of India",   "ltp": 298.60,  "change_pct": 1.44, "volume": 11_300_000},
        ],
        "losers": [
            {"symbol": "INFY",      "company": "Infosys Ltd",                "ltp": 1385.40, "change_pct": -2.45, "volume": 9_800_000},
            {"symbol": "ITC",       "company": "ITC Ltd",                    "ltp": 432.15,  "change_pct": -1.98, "volume": 28_500_000},
            {"symbol": "TCS",       "company": "Tata Consultancy Svcs Ltd",  "ltp": 4128.60, "change_pct": -1.72, "volume": 3_200_000},
            {"symbol": "ONGC",      "company": "Oil & Natural Gas Corp Ltd", "ltp": 214.30,  "change_pct": -1.58, "volume": 18_700_000},
            {"symbol": "COALINDIA", "company": "Coal India Ltd",             "ltp": 387.25,  "change_pct": -1.42, "volume": 12_300_000},
            {"symbol": "BPCL",      "company": "BPCL Ltd",                   "ltp": 312.45,  "change_pct": -1.31, "volume": 9_100_000},
            {"symbol": "IOC",       "company": "Indian Oil Corp Ltd",        "ltp": 142.80,  "change_pct": -1.19, "volume": 35_400_000},
            {"symbol": "JSWSTEEL",  "company": "JSW Steel Ltd",              "ltp": 812.30,  "change_pct": -1.08, "volume": 5_600_000},
            {"symbol": "SBIN",      "company": "State Bank of India",        "ltp": 762.40,  "change_pct": -0.95, "volume": 24_200_000},
            {"symbol": "HINDALCO",  "company": "Hindalco Industries Ltd",    "ltp": 578.90,  "change_pct": -0.84, "volume": 7_800_000},
        ],
    },

    # ── FII / DII data (last 30 days in ₹ Cr) ─────────────────────────────
    "fii_dii_data": [
        {
            "date": (datetime(2025, 1, 20) - timedelta(days=i)).strftime("%d-%b-%Y"),
            "fii_buy":  round(random.uniform(8000, 18000), 2),
            "fii_sell": round(random.uniform(7000, 17000), 2),
            "fii_net":  round(random.gauss(500, 2500), 2),
            "dii_buy":  round(random.uniform(6000, 12000), 2),
            "dii_sell": round(random.uniform(5000, 10000), 2),
            "dii_net":  round(random.gauss(1200, 1800), 2),
        }
        for i in range(30)
    ],

    # ── Bulk deals ──────────────────────────────────────────────────────────
    "bulk_deals": [
        {"symbol": "HDFCBANK",  "client_name": "Mirae Asset Mutual Fund",      "buy_sell": "BUY",  "quantity": 5_000_000, "price": 1712.40, "value_cr": 856.20,  "date": "17-Jan-2025", "deal_type": "BULK"},
        {"symbol": "INFY",      "client_name": "SBI Mutual Fund",              "buy_sell": "SELL", "quantity": 3_000_000, "price": 1418.50, "value_cr": 425.55,  "date": "17-Jan-2025", "deal_type": "BULK"},
        {"symbol": "RELIANCE",  "client_name": "HDFC Mutual Fund",             "buy_sell": "BUY",  "quantity": 2_500_000, "price": 2934.55, "value_cr": 733.64,  "date": "16-Jan-2025", "deal_type": "BULK"},
        {"symbol": "TCS",       "client_name": "Nippon India Mutual Fund",     "buy_sell": "BUY",  "quantity": 800_000,   "price": 4156.80, "value_cr": 332.54,  "date": "16-Jan-2025", "deal_type": "BULK"},
        {"symbol": "BAJFINANCE","client_name": "Axis Mutual Fund",             "buy_sell": "BUY",  "quantity": 600_000,   "price": 6984.30, "value_cr": 419.06,  "date": "15-Jan-2025", "deal_type": "BULK"},
        {"symbol": "WIPRO",     "client_name": "Goldman Sachs (Mauritius)",    "buy_sell": "SELL", "quantity": 4_200_000, "price": 487.50,  "value_cr": 204.75,  "date": "15-Jan-2025", "deal_type": "BULK"},
        {"symbol": "ADANIENT",  "client_name": "Franklin Templeton MF",        "buy_sell": "BUY",  "quantity": 1_200_000, "price": 2436.10, "value_cr": 292.33,  "date": "14-Jan-2025", "deal_type": "BULK"},
        {"symbol": "ICICIBANK", "client_name": "ICICI Prudential Mutual Fund", "buy_sell": "BUY",  "quantity": 3_500_000, "price": 1224.30, "value_cr": 428.51,  "date": "14-Jan-2025", "deal_type": "BULK"},
        {"symbol": "SBIN",      "client_name": "Life Insurance Corp of India", "buy_sell": "BUY",  "quantity": 8_000_000, "price": 762.40,  "value_cr": 609.92,  "date": "13-Jan-2025", "deal_type": "BULK"},
        {"symbol": "LT",        "client_name": "DSP Mutual Fund",              "buy_sell": "SELL", "quantity": 900_000,   "price": 3547.20, "value_cr": 319.25,  "date": "13-Jan-2025", "deal_type": "BULK"},
        {"symbol": "TATAMOTORS","client_name": "Avendus Capital Pte Ltd",      "buy_sell": "BUY",  "quantity": 6_000_000, "price": 876.45,  "value_cr": 525.87,  "date": "10-Jan-2025", "deal_type": "BULK"},
        {"symbol": "SUNPHARMA", "client_name": "Kotak Mahindra MF",            "buy_sell": "BUY",  "quantity": 1_500_000, "price": 1654.80, "value_cr": 248.22,  "date": "10-Jan-2025", "deal_type": "BULK"},
    ],

    # ── Block deals ─────────────────────────────────────────────────────────
    "block_deals": [
        {"symbol": "ZOMATO",    "client_name": "Morgan Stanley Asia",          "buy_sell": "BUY",  "quantity": 25_000_000, "price": 234.50,  "value_cr": 586.25,  "date": "17-Jan-2025", "deal_type": "BLOCK"},
        {"symbol": "PAYTM",     "client_name": "Antfin Netherlands Holding",   "buy_sell": "SELL", "quantity": 18_000_000, "price": 812.30,  "value_cr": 1462.14, "date": "16-Jan-2025", "deal_type": "BLOCK"},
        {"symbol": "NYKAA",     "client_name": "TPG Growth IV SF Pte Ltd",     "buy_sell": "SELL", "quantity": 12_000_000, "price": 187.60,  "value_cr": 225.12,  "date": "15-Jan-2025", "deal_type": "BLOCK"},
        {"symbol": "DELHIVERY", "client_name": "SoftBank Vision Fund",         "buy_sell": "SELL", "quantity": 8_500_000,  "price": 364.80,  "value_cr": 310.08,  "date": "14-Jan-2025", "deal_type": "BLOCK"},
        {"symbol": "IRCTC",     "client_name": "Govt of India (Divestment)",   "buy_sell": "SELL", "quantity": 5_000_000,  "price": 786.40,  "value_cr": 393.20,  "date": "13-Jan-2025", "deal_type": "BLOCK"},
        {"symbol": "HAL",       "client_name": "Govt of India (Divestment)",   "buy_sell": "SELL", "quantity": 2_000_000,  "price": 4218.60, "value_cr": 843.72,  "date": "10-Jan-2025", "deal_type": "BLOCK"},
        {"symbol": "PERSISTENT","client_name": "Nomura Singapore Ltd",         "buy_sell": "BUY",  "quantity": 1_200_000,  "price": 5634.20, "value_cr": 676.10,  "date": "10-Jan-2025", "deal_type": "BLOCK"},
        {"symbol": "TRENT",     "client_name": "GQG Partners LLC",             "buy_sell": "BUY",  "quantity": 3_000_000,  "price": 4876.50, "value_cr": 1462.95, "date": "09-Jan-2025", "deal_type": "BLOCK"},
    ],

    # ── Insider trades ──────────────────────────────────────────────────────
    "insider_trades": [
        {"symbol": "BAJAJFINSV", "person_name": "Bajaj Finserv Ltd (Promoter)", "category": "Promoter",         "trade_type": "BUY",  "quantity": 450_000,   "value_cr": 78.42,  "date": "17-Jan-2025", "pre_holding_pct": 60.78, "post_holding_pct": 60.82, "mode": "Market Purchase"},
        {"symbol": "SUNPHARMA",  "person_name": "Dilip S Shanghvi",              "category": "Promoter",         "trade_type": "BUY",  "quantity": 2_000_000, "value_cr": 330.96, "date": "16-Jan-2025", "pre_holding_pct": 54.48, "post_holding_pct": 54.52, "mode": "Market Purchase"},
        {"symbol": "PERSISTENT", "person_name": "Dr Anand Deshpande",            "category": "Promoter",         "trade_type": "BUY",  "quantity": 50_000,    "value_cr": 28.17,  "date": "15-Jan-2025", "pre_holding_pct": 30.81, "post_holding_pct": 30.82, "mode": "Market Purchase"},
        {"symbol": "INFY",       "person_name": "Salil S Parekh",                "category": "Key Managerial",   "trade_type": "SELL", "quantity": 300_000,   "value_cr": 42.56,  "date": "15-Jan-2025", "pre_holding_pct": 0.31,  "post_holding_pct": 0.28,  "mode": "ESOP Exercise"},
        {"symbol": "HDFCBANK",   "person_name": "Sashidhar Jagdishan",           "category": "Key Managerial",   "trade_type": "SELL", "quantity": 120_000,   "value_cr": 20.55,  "date": "14-Jan-2025", "pre_holding_pct": 0.08,  "post_holding_pct": 0.07,  "mode": "ESOP Exercise"},
        {"symbol": "ZOMATO",     "person_name": "Deepinder Goyal",               "category": "Promoter",         "trade_type": "BUY",  "quantity": 5_000_000, "value_cr": 117.25, "date": "13-Jan-2025", "pre_holding_pct": 4.12,  "post_holding_pct": 4.16,  "mode": "Market Purchase"},
        {"symbol": "WHIRLPOOL",  "person_name": "Whirlpool Corp USA",            "category": "Promoter",         "trade_type": "SELL", "quantity": 8_000_000, "value_cr": 152.00, "date": "13-Jan-2025", "pre_holding_pct": 51.00, "post_holding_pct": 48.00, "mode": "Off-Market"},
        {"symbol": "IRCTC",      "person_name": "President of India",            "category": "Promoter (Govt)",  "trade_type": "SELL", "quantity": 5_000_000, "value_cr": 393.20, "date": "10-Jan-2025", "pre_holding_pct": 67.46, "post_holding_pct": 67.08, "mode": "OFS"},
        {"symbol": "COFORGE",    "person_name": "Baring Private Equity Asia",    "category": "Institutional",    "trade_type": "SELL", "quantity": 1_500_000, "value_cr": 108.15, "date": "10-Jan-2025", "pre_holding_pct": 12.28, "post_holding_pct": 11.16, "mode": "Block Deal"},
        {"symbol": "TATATECH",   "person_name": "Tata Motors Ltd",               "category": "Promoter",         "trade_type": "BUY",  "quantity": 10_000_000,"value_cr": 112.80, "date": "09-Jan-2025", "pre_holding_pct": 46.42, "post_holding_pct": 46.72, "mode": "Market Purchase"},
    ],

    # ── Corporate filings ───────────────────────────────────────────────────
    "corporate_filings": [
        {"symbol": "RELIANCE",  "company": "Reliance Industries Ltd",          "category": "Financial Results",  "headline": "Q3FY25 Net Profit ₹18,540 Cr, Revenue ₹2.31 Lakh Cr",               "date": "17-Jan-2025", "subject": "Q3FY25 Financial Results"},
        {"symbol": "TCS",       "company": "Tata Consultancy Services Ltd",    "category": "Financial Results",  "headline": "Q3FY25 PAT ₹12,380 Cr (+5.4% YoY), Revenue $7.56B",                 "date": "16-Jan-2025", "subject": "Q3FY25 Financial Results"},
        {"symbol": "INFY",      "company": "Infosys Ltd",                      "category": "Financial Results",  "headline": "Q3FY25 PAT ₹6,806 Cr, Revenue Guidance Upgraded to 4.5-5%",        "date": "16-Jan-2025", "subject": "Q3FY25 Results and Guidance Update"},
        {"symbol": "ADANIENT",  "company": "Adani Enterprises Ltd",            "category": "Acquisition",        "headline": "Enters AI Data Centre Business; JV with Google Cloud",               "date": "15-Jan-2025", "subject": "Joint Venture Announcement"},
        {"symbol": "HDFCBANK",  "company": "HDFC Bank Ltd",                    "category": "Board Meeting",      "headline": "Dividend of ₹19 Per Share Declared for Q3FY25",                     "date": "15-Jan-2025", "subject": "Dividend Declaration"},
        {"symbol": "TCS",       "company": "Tata Consultancy Services Ltd",    "category": "Insider Trading",    "headline": "Director Milind Lakkad Sells 50,000 Shares via ESOP",               "date": "14-Jan-2025", "subject": "Insider Trading Disclosure"},
        {"symbol": "HAL",       "company": "Hindustan Aeronautics Ltd",        "category": "Acquisition",        "headline": "₹21,935 Cr Order from Ministry of Defence for 12 Sukhoi Jets",      "date": "14-Jan-2025", "subject": "Major Order Win"},
        {"symbol": "LTIM",      "company": "LTIMindtree Ltd",                  "category": "Financial Results",  "headline": "Q3FY25 PAT ₹1,164 Cr (+7.8%), Strong Deal Wins in BFSI",           "date": "13-Jan-2025", "subject": "Q3FY25 Financial Results"},
        {"symbol": "ZOMATO",    "company": "Zomato Ltd",                       "category": "Board Meeting",      "headline": "Board Approves QIP to Raise ₹8,500 Cr at ₹250/share",             "date": "13-Jan-2025", "subject": "QIP Announcement"},
        {"symbol": "BAJFINANCE","company": "Bajaj Finance Ltd",                "category": "Regulatory",         "headline": "RBI Removes Restrictions on eCOM and Insta EMI Card Products",      "date": "10-Jan-2025", "subject": "Regulatory Update"},
        {"symbol": "RVNL",      "company": "Rail Vikas Nigam Ltd",             "category": "Acquisition",        "headline": "₹4,200 Cr Contract from Railways for Electrification Projects",     "date": "10-Jan-2025", "subject": "Order Win"},
        {"symbol": "WIPRO",     "company": "Wipro Ltd",                        "category": "Financial Results",  "headline": "Q3FY25 IT Services Revenue $2.63B; US Market Recovery Seen",        "date": "10-Jan-2025", "subject": "Q3FY25 Financial Results"},
        {"symbol": "NYKAA",     "company": "FSN E-Commerce Ventures Ltd",      "category": "Board Meeting",      "headline": "Bonus Issue 5:1 Approved; Record Date Feb 14, 2025",                "date": "09-Jan-2025", "subject": "Bonus Share Announcement"},
        {"symbol": "TATASTEEL", "company": "Tata Steel Ltd",                   "category": "Regulatory",         "headline": "UK Govt Approves £500M Grant for Port Talbot Green Steel Project",  "date": "09-Jan-2025", "subject": "Regulatory Approval"},
        {"symbol": "IRFC",      "company": "Indian Railway Finance Corp Ltd",  "category": "Financial Results",  "headline": "Q3FY25 PAT ₹1,629 Cr (+4.1% YoY), Loan Book Expands 15%",          "date": "08-Jan-2025", "subject": "Q3FY25 Financial Results"},
    ],

    # ── IPO data ────────────────────────────────────────────────────────────
    "ipo_data": {
        "current": [
            {
                "company": "Denta Water and Infra Solutions Ltd", "symbol": "DENTAWATER",
                "open_date": "22-Jan-2025", "close_date": "24-Jan-2025",
                "issue_price": "279-294", "lot_size": 50, "issue_size_cr": 195.90,
                "status": "CURRENT", "subscription_times": None, "listing_date": None,
            },
            {
                "company": "Sat Kartar Shopping Ltd", "symbol": "SATKARSHO",
                "open_date": "22-Jan-2025", "close_date": "24-Jan-2025",
                "issue_price": "96-101",   "lot_size": 1200, "issue_size_cr": 54.60,
                "status": "CURRENT", "subscription_times": None, "listing_date": None,
            },
        ],
        "upcoming": [
            {
                "company": "Hexaware Technologies Ltd", "symbol": "HEXAWARE",
                "open_date": "12-Feb-2025", "close_date": "14-Feb-2025",
                "issue_price": "674-708",  "lot_size": 21,  "issue_size_cr": 8750.00,
                "status": "UPCOMING", "subscription_times": None, "listing_date": None,
            },
            {
                "company": "LG Electronics India Ltd", "symbol": "LGINDO",
                "open_date": "10-Mar-2025", "close_date": "12-Mar-2025",
                "issue_price": None, "lot_size": None, "issue_size_cr": 15000.00,
                "status": "UPCOMING", "subscription_times": None, "listing_date": None,
            },
            {
                "company": "Ather Energy Ltd", "symbol": "ATHER",
                "open_date": "28-Feb-2025", "close_date": "03-Mar-2025",
                "issue_price": "304-321",  "lot_size": 46,  "issue_size_cr": 2981.00,
                "status": "UPCOMING", "subscription_times": None, "listing_date": None,
            },
        ],
        "listed": [
            {"company": "Standard Glass Lining Technology", "symbol": "SGL",   "listing_date": "20-Jan-2025", "listing_price": 175.00, "listing_gain_pct": 40.00,  "issue_price": "125-133", "status": "LISTED"},
            {"company": "Stallion India Fluorochemicals",   "symbol": "SFCL",  "listing_date": "16-Jan-2025", "listing_price": 134.00, "listing_gain_pct": 12.61,  "issue_price": "85-90",   "status": "LISTED"},
            {"company": "Mobikwik",                         "symbol": "MBK",   "listing_date": "18-Dec-2024", "listing_price": 442.25, "listing_gain_pct": 57.30,  "issue_price": "265-279", "status": "LISTED"},
            {"company": "Vishal Mega Mart",                 "symbol": "VMM",   "listing_date": "18-Dec-2024", "listing_price": 109.50, "listing_gain_pct": 37.61,  "issue_price": "74-78",   "status": "LISTED"},
            {"company": "Bajaj Housing Finance",            "symbol": "BAJAJHFL","listing_date": "16-Sep-2024","listing_price": 150.00, "listing_gain_pct": 114.29, "issue_price": "66-70",   "status": "LISTED"},
        ],
    },

    # ── Sector performance ──────────────────────────────────────────────────
    "sector_performance": [
        {"sector": "IT",      "return_1d_pct": -1.25, "return_1w_pct": -2.10, "return_1m_pct": 4.32,  "top_stock": "TCS"},
        {"sector": "Banking", "return_1d_pct": 0.87,  "return_1w_pct": 1.45,  "return_1m_pct": -1.23, "top_stock": "HDFCBANK"},
        {"sector": "Pharma",  "return_1d_pct": 1.95,  "return_1w_pct": 3.21,  "return_1m_pct": 6.78,  "top_stock": "SUNPHARMA"},
        {"sector": "Auto",    "return_1d_pct": 2.18,  "return_1w_pct": 4.32,  "return_1m_pct": 8.45,  "top_stock": "TATAMOTORS"},
        {"sector": "FMCG",   "return_1d_pct": -0.54, "return_1w_pct": -0.87, "return_1m_pct": 2.14,  "top_stock": "HINDUNILVR"},
        {"sector": "Energy",  "return_1d_pct": 0.34,  "return_1w_pct": 0.92,  "return_1m_pct": -2.87, "top_stock": "RELIANCE"},
        {"sector": "Metals",  "return_1d_pct": -1.08, "return_1w_pct": -2.34, "return_1m_pct": -4.12, "top_stock": "TATASTEEL"},
        {"sector": "Realty",  "return_1d_pct": 1.42,  "return_1w_pct": 2.87,  "return_1m_pct": 5.63,  "top_stock": "DLF"},
        {"sector": "Infra",   "return_1d_pct": 1.78,  "return_1w_pct": 3.54,  "return_1m_pct": 7.23,  "top_stock": "LT"},
    ],

    # ── OHLCV data ──────────────────────────────────────────────────────────
    "ohlcv": {
        "RELIANCE":  _ohlcv_series(2480, days=400, trend=0.0004, vol=0.014),
        "TCS":       _ohlcv_series(3870, days=400, trend=0.0002, vol=0.012),
        "HDFCBANK":  _ohlcv_series(1570, days=400, trend=0.0003, vol=0.013),
        "INFY":      _ohlcv_series(1390, days=400, trend=0.0001, vol=0.015),
        "ICICIBANK": _ohlcv_series(1050, days=400, trend=0.0005, vol=0.014),
    },

    # ── Fundamentals ────────────────────────────────────────────────────────
    "fundamentals": {
        "RELIANCE": {
            "symbol": "RELIANCE", "company_name": "Reliance Industries Ltd",
            "sector": "Energy", "industry": "Oil & Gas Integrated",
            "market_cap_cr": 1_965_432, "current_price": 2934.55,
            "pe_ratio": 27.8, "pb_ratio": 2.3, "roe_pct": 9.8,
            "debt_equity": 0.48, "revenue_growth": 8.2, "earnings_growth": 12.4,
            "52w_high": 3217.90, "52w_low": 2220.30,
            "avg_volume": 4_800_000, "dividend_yield": 0.34, "beta": 0.82,
            "description": "Reliance Industries is India's largest conglomerate with operations spanning petrochemicals, refining, oil, telecommunications, and retail.",
        },
        "TCS": {
            "symbol": "TCS", "company_name": "Tata Consultancy Services Ltd",
            "sector": "Technology", "industry": "IT Services",
            "market_cap_cr": 1_452_300, "current_price": 4128.60,
            "pe_ratio": 31.2, "pb_ratio": 15.4, "roe_pct": 48.2,
            "debt_equity": 0.03, "revenue_growth": 6.8, "earnings_growth": 8.1,
            "52w_high": 4592.25, "52w_low": 3311.00,
            "avg_volume": 3_200_000, "dividend_yield": 1.82, "beta": 0.71,
            "description": "TCS is India's largest IT services company providing software, IT, and IT-enabled services globally.",
        },
        "HDFCBANK": {
            "symbol": "HDFCBANK", "company_name": "HDFC Bank Ltd",
            "sector": "Financial Services", "industry": "Private Bank",
            "market_cap_cr": 1_248_000, "current_price": 1648.25,
            "pe_ratio": 18.4, "pb_ratio": 2.8, "roe_pct": 16.2,
            "debt_equity": None, "revenue_growth": 14.5, "earnings_growth": 11.8,
            "52w_high": 1794.00, "52w_low": 1363.55,
            "avg_volume": 12_400_000, "dividend_yield": 1.12, "beta": 1.04,
            "description": "India's largest private sector bank with operations in retail banking, wholesale banking, treasury, and digital payments.",
        },
        "INFY": {
            "symbol": "INFY", "company_name": "Infosys Ltd",
            "sector": "Technology", "industry": "IT Services",
            "market_cap_cr": 578_000, "current_price": 1385.40,
            "pe_ratio": 28.9, "pb_ratio": 9.1, "roe_pct": 32.4,
            "debt_equity": 0.07, "revenue_growth": 4.5, "earnings_growth": 7.2,
            "52w_high": 1903.75, "52w_low": 1358.35,
            "avg_volume": 9_800_000, "dividend_yield": 2.41, "beta": 0.78,
            "description": "Infosys is a global IT services and consulting company providing digital transformation and IT infrastructure services.",
        },
        "ICICIBANK": {
            "symbol": "ICICIBANK", "company_name": "ICICI Bank Ltd",
            "sector": "Financial Services", "industry": "Private Bank",
            "market_cap_cr": 884_500, "current_price": 1224.30,
            "pe_ratio": 17.2, "pb_ratio": 3.2, "roe_pct": 18.7,
            "debt_equity": None, "revenue_growth": 16.8, "earnings_growth": 14.2,
            "52w_high": 1329.00, "52w_low": 970.05,
            "avg_volume": 14_200_000, "dividend_yield": 0.82, "beta": 1.12,
            "description": "ICICI Bank is India's second largest private sector bank with a diversified portfolio of loans, investments, and digital banking.",
        },
    },

    # ── Stock quotes ────────────────────────────────────────────────────────
    "stock_quotes": {
        "RELIANCE":  {"symbol": "RELIANCE",  "ltp": 2934.55, "change": 24.50,  "change_pct": 0.84,  "open": 2910.05, "high": 2948.90, "low": 2908.00, "prev_close": 2910.05, "volume": 4_812_345,  "52w_high": 3217.90, "52w_low": 2220.30, "timestamp": "2025-01-20T10:30:00+05:30"},
        "TCS":       {"symbol": "TCS",       "ltp": 4128.60, "change": -12.30, "change_pct": -0.29, "open": 4144.00, "high": 4155.80, "low": 4121.15, "prev_close": 4140.90, "volume": 3_241_500,  "52w_high": 4592.25, "52w_low": 3311.00, "timestamp": "2025-01-20T10:30:00+05:30"},
        "HDFCBANK":  {"symbol": "HDFCBANK",  "ltp": 1648.25, "change": 51.25,  "change_pct": 3.21,  "open": 1608.30, "high": 1654.90, "low": 1606.00, "prev_close": 1597.00, "volume": 12_456_780, "52w_high": 1794.00, "52w_low": 1363.55, "timestamp": "2025-01-20T10:30:00+05:30"},
        "INFY":      {"symbol": "INFY",      "ltp": 1385.40, "change": -34.90, "change_pct": -2.45, "open": 1418.50, "high": 1422.00, "low": 1381.20, "prev_close": 1420.30, "volume": 9_876_543,  "52w_high": 1903.75, "52w_low": 1358.35, "timestamp": "2025-01-20T10:30:00+05:30"},
        "ICICIBANK": {"symbol": "ICICIBANK", "ltp": 1224.30, "change": 14.80,  "change_pct": 1.22,  "open": 1210.00, "high": 1228.90, "low": 1208.55, "prev_close": 1209.50, "volume": 14_231_000, "52w_high": 1329.00, "52w_low": 970.05,  "timestamp": "2025-01-20T10:30:00+05:30"},
        "BAJFINANCE":{"symbol": "BAJFINANCE","ltp": 6984.30, "change": 157.40, "change_pct": 2.31,  "open": 6828.00, "high": 6998.00, "low": 6820.10, "prev_close": 6826.90, "volume": 2_145_678,  "52w_high": 7830.00, "52w_low": 6187.80, "timestamp": "2025-01-20T10:30:00+05:30"},
        "SBIN":      {"symbol": "SBIN",      "ltp": 762.40,  "change": -7.30,  "change_pct": -0.95, "open": 771.00,  "high": 773.50,  "low": 760.00,  "prev_close": 769.70,  "volume": 24_123_456, "52w_high": 912.10,  "52w_low": 600.65,  "timestamp": "2025-01-20T10:30:00+05:30"},
        "TATAMOTORS":{"symbol": "TATAMOTORS","ltp": 876.45,  "change": 18.75,  "change_pct": 2.18,  "open": 858.00,  "high": 881.50,  "low": 856.20,  "prev_close": 857.70,  "volume": 15_678_901, "52w_high": 1179.00, "52w_low": 718.85,  "timestamp": "2025-01-20T10:30:00+05:30"},
        "ADANIENT":  {"symbol": "ADANIENT",  "ltp": 2436.10, "change": 60.20,  "change_pct": 2.54,  "open": 2376.50, "high": 2448.00, "low": 2371.00, "prev_close": 2375.90, "volume": 4_567_890,  "52w_high": 3743.90, "52w_low": 2025.50, "timestamp": "2025-01-20T10:30:00+05:30"},
        "WIPRO":     {"symbol": "WIPRO",     "ltp": 487.50,  "change": 13.60,  "change_pct": 2.87,  "open": 474.00,  "high": 489.90,  "low": 473.20,  "prev_close": 473.90,  "volume": 8_234_567,  "52w_high": 583.90,  "52w_low": 391.20,  "timestamp": "2025-01-20T10:30:00+05:30"},
        "SUNPHARMA": {"symbol": "SUNPHARMA", "ltp": 1654.80, "change": 31.70,  "change_pct": 1.95,  "open": 1624.50, "high": 1661.00, "low": 1621.00, "prev_close": 1623.10, "volume": 3_456_789,  "52w_high": 1960.35, "52w_low": 1240.25, "timestamp": "2025-01-20T10:30:00+05:30"},
        "LT":        {"symbol": "LT",        "ltp": 3547.20, "change": 62.10,  "change_pct": 1.78,  "open": 3487.00, "high": 3558.90, "low": 3482.00, "prev_close": 3485.10, "volume": 2_876_543,  "52w_high": 3963.95, "52w_low": 2700.80, "timestamp": "2025-01-20T10:30:00+05:30"},
        "ITC":       {"symbol": "ITC",       "ltp": 432.15,  "change": -8.70,  "change_pct": -1.98, "open": 441.00,  "high": 441.90,  "low": 430.50,  "prev_close": 440.85,  "volume": 28_456_123, "52w_high": 528.50,  "52w_low": 399.35,  "timestamp": "2025-01-20T10:30:00+05:30"},
        "ONGC":      {"symbol": "ONGC",      "ltp": 214.30,  "change": -3.45,  "change_pct": -1.58, "open": 218.00,  "high": 218.50,  "low": 213.80,  "prev_close": 217.75,  "volume": 18_765_432, "52w_high": 345.00,  "52w_low": 196.20,  "timestamp": "2025-01-20T10:30:00+05:30"},
        "AXISBANK":  {"symbol": "AXISBANK",  "ltp": 1082.50, "change": 8.90,   "change_pct": 0.83,  "open": 1074.00, "high": 1087.90, "low": 1071.00, "prev_close": 1073.60, "volume": 7_891_234,  "52w_high": 1339.65, "52w_low": 995.65,  "timestamp": "2025-01-20T10:30:00+05:30"},
        "KOTAKBANK": {"symbol": "KOTAKBANK", "ltp": 1756.40, "change": 14.30,  "change_pct": 0.82,  "open": 1744.00, "high": 1762.30, "low": 1740.50, "prev_close": 1742.10, "volume": 5_432_100,  "52w_high": 2063.35, "52w_low": 1543.85, "timestamp": "2025-01-20T10:30:00+05:30"},
        "HINDUNILVR":{"symbol": "HINDUNILVR","ltp": 2342.80, "change": -13.20, "change_pct": -0.56, "open": 2358.00, "high": 2362.00, "low": 2338.50, "prev_close": 2356.00, "volume": 1_234_567,  "52w_high": 2852.00, "52w_low": 2172.05, "timestamp": "2025-01-20T10:30:00+05:30"},
        "BAJAJHFL":  {"symbol": "BAJAJHFL",  "ltp": 128.30,  "change": 1.45,   "change_pct": 1.14,  "open": 127.00,  "high": 129.50,  "low": 126.60,  "prev_close": 126.85,  "volume": 45_678_901, "52w_high": 188.65,  "52w_low": 58.45,   "timestamp": "2025-01-20T10:30:00+05:30"},
        "NTPC":      {"symbol": "NTPC",      "ltp": 348.75,  "change": 5.20,   "change_pct": 1.51,  "open": 344.00,  "high": 350.10,  "low": 343.20,  "prev_close": 343.55,  "volume": 22_123_456, "52w_high": 448.45,  "52w_low": 246.85,  "timestamp": "2025-01-20T10:30:00+05:30"},
        "MARUTI":    {"symbol": "MARUTI",    "ltp": 11245.00,"change": 187.50, "change_pct": 1.69,  "open": 11058.00,"high": 11298.00,"low": 11045.00,"prev_close": 11057.50, "volume": 456_789,   "52w_high": 13680.00, "52w_low": 9756.00, "timestamp": "2025-01-20T10:30:00+05:30"},
        "ZOMATO":    {"symbol": "ZOMATO",    "ltp": 234.50,  "change": 4.80,   "change_pct": 2.09,  "open": 229.80,  "high": 236.40,  "low": 229.00,  "prev_close": 229.70,  "volume": 42_567_890, "52w_high": 304.70,  "52w_low": 143.10,  "timestamp": "2025-01-20T10:30:00+05:30"},
    },

    # ── Multiple quotes (for batch) ──────────────────────────────────────────
    "multiple_quotes": [
        {"symbol": "RELIANCE",  "ltp": 2934.55, "change": 24.50,  "change_pct": 0.84,  "volume": 4_812_345,  "high": 2948.90, "low": 2908.00, "timestamp": "2025-01-20T10:30:00+05:30"},
        {"symbol": "TCS",       "ltp": 4128.60, "change": -12.30, "change_pct": -0.29, "volume": 3_241_500,  "high": 4155.80, "low": 4121.15, "timestamp": "2025-01-20T10:30:00+05:30"},
        {"symbol": "HDFCBANK",  "ltp": 1648.25, "change": 51.25,  "change_pct": 3.21,  "volume": 12_456_780, "high": 1654.90, "low": 1606.00, "timestamp": "2025-01-20T10:30:00+05:30"},
        {"symbol": "INFY",      "ltp": 1385.40, "change": -34.90, "change_pct": -2.45, "volume": 9_876_543,  "high": 1422.00, "low": 1381.20, "timestamp": "2025-01-20T10:30:00+05:30"},
        {"symbol": "ICICIBANK", "ltp": 1224.30, "change": 14.80,  "change_pct": 1.22,  "volume": 14_231_000, "high": 1228.90, "low": 1208.55, "timestamp": "2025-01-20T10:30:00+05:30"},
    ],
}
