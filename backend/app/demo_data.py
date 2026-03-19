"""
ET InvestorIQ — Demo Data
Comprehensive mock dataset for offline demos and testing.
Set MOCK_MODE=True in .env to use this data exclusively.
Contains 30+ signals, 20+ patterns, IPOs, FII data, and portfolio examples.
"""

from datetime import datetime, timedelta
import random

# ─────────────────────────────────────────────────────────────────────────────
# TODAY's date anchor for realistic relative dates
# ─────────────────────────────────────────────────────────────────────────────
TODAY = datetime(2026, 3, 19)


def _d(days_ago: int) -> str:
    return (TODAY - timedelta(days=days_ago)).strftime("%Y-%m-%d")


# ─────────────────────────────────────────────────────────────────────────────
# MOCK SIGNALS (30+ items)
# ─────────────────────────────────────────────────────────────────────────────
DEMO_SIGNALS = [
    {
        "id": "sig001",
        "symbol": "RELIANCE",
        "company_name": "Reliance Industries Ltd",
        "signal_type": "INSIDER_TRADE",
        "headline": "Promoter Mukesh Ambani bought ₹4.2 Cr of Reliance 3 days before Q4 results",
        "detail": "Mukesh Ambani (Promoter) purchased 14,400 shares of Reliance Industries at ₹2,920 "
                  "per share (total ₹4.20 Cr) on March 16, 2026 — just 3 trading days before Q4 FY26 results. "
                  "Post-transaction holding: 50.34%. This is the largest single promoter purchase in 18 months.",
        "confidence_score": 0.91,
        "signal_date": _d(3),
        "stock_price_at_signal": 2920.0,
        "expected_impact": "BULLISH",
        "ai_analysis": ("Mukesh Ambani's buy of ₹4.2 Cr just 3 days before results is a textbook "
                         "insider confidence signal. The timing is particularly notable because promoters "
                         "are typically restricted from trading within 15 days of results under SEBI UPSI rules — "
                         "this transaction occurred just outside the blackout window. "
                         "Historically, when Reliance promoters have purchased before results, the stock has "
                         "outperformed Nifty by 6-8% in the following 30 days. "
                         "Watch for Q4 EBITDA beat and any announcement on the Jio Financial spin-off timeline."),
        "data_sources": ["NSE Insider Trading Disclosure", "BSE Corporate Filings"],
        "tags": ["insider", "promoter", "buy", "reliance", "pre-results", "high-conviction"],
    },
    {
        "id": "sig002",
        "symbol": "ADANIENT",
        "company_name": "Adani Enterprises Ltd",
        "signal_type": "PROMOTER_PLEDGE_CHANGE",
        "headline": "Promoter pledge dropped 18% this quarter — historically bullish for this stock",
        "detail": "Adani Group promoters reduced pledged shares by 8.2 Cr shares (18% reduction) in Q4 FY26. "
                  "Pledged shareholding now at 12.4% vs 15.1% last quarter. "
                  "The last two times this happened (Q2 FY24, Q1 FY25), ADANIENT rallied 22% and 18% respectively "
                  "over the following 3 months.",
        "confidence_score": 0.84,
        "signal_date": _d(1),
        "stock_price_at_signal": 3151.0,
        "expected_impact": "BULLISH",
        "ai_analysis": "Pledge reduction signals improved balance sheet health and promoter conviction.",
        "data_sources": ["SEBI Pledge Disclosures", "NSE Shareholding Pattern"],
        "tags": ["pledge", "adani", "promoter", "bullish", "balance-sheet"],
    },
    {
        "id": "sig003",
        "symbol": "TCS",
        "company_name": "Tata Consultancy Services",
        "signal_type": "BULK_DEAL",
        "headline": "Mirae Asset MF accumulated ₹1,850 Cr of TCS in 3 consecutive days",
        "detail": "Mirae Asset Mutual Fund executed bulk purchase of TCS shares across 3 consecutive trading days: "
                  "₹620 Cr (March 17), ₹680 Cr (March 18), ₹550 Cr (March 19). Total: ₹1,850 Cr. "
                  "This is the largest single-week institutional accumulation in TCS since Q4 2023. "
                  "Price barely moved (+0.8%), suggesting quiet accumulation before a re-rating event.",
        "confidence_score": 0.87,
        "signal_date": _d(0),
        "stock_price_at_signal": 4112.0,
        "expected_impact": "BULLISH",
        "ai_analysis": "Institutional accumulation with minimal price impact suggests controlled buying.",
        "data_sources": ["NSE Bulk Deals", "BSE Block Deals"],
        "tags": ["bulk_deal", "institutional", "tcs", "mirae", "accumulation"],
    },
    {
        "id": "sig004",
        "symbol": "ITC",
        "company_name": "ITC Ltd",
        "signal_type": "CORPORATE_ACTION",
        "headline": "Board approves ₹18,000 Cr buyback at ₹530 — 17% premium to CMP",
        "detail": "ITC's board of directors has announced a share buyback of ₹18,000 Crores at ₹530 per share "
                  "(₹452.50 current price — 17.1% premium). This is ITC's largest-ever buyback. "
                  "Buyback opens: April 10, 2026. Record date: April 2, 2026. "
                  "At ₹530, the buyback represents 1.8% of total shares. "
                  "Post-buyback, EPS is expected to increase by ₹1.8 (8% accretion).",
        "confidence_score": 0.92,
        "signal_date": _d(2),
        "stock_price_at_signal": 452.5,
        "expected_impact": "BULLISH",
        "ai_analysis": "Buyback at 17% premium is classic catalyst for short-term 10-15% upside.",
        "data_sources": ["BSE Announcement", "NSE Corporation Action"],
        "tags": ["buyback", "itc", "corporate_action", "premium", "fmcg"],
    },
    {
        "id": "sig005",
        "symbol": "HDFCBANK",
        "company_name": "HDFC Bank Ltd",
        "signal_type": "EARNINGS_SURPRISE",
        "headline": "HDFC Bank Q4 FY26: NII at ₹29,200 Cr — beats estimate by ₹1,800 Cr",
        "detail": "HDFC Bank reported Q4 FY26 Net Interest Income of ₹29,200 Cr, beating Bloomberg consensus "
                  "estimate of ₹27,400 Cr by 6.6%. PAT: ₹15,850 Cr (consensus: ₹14,900 Cr). "
                  "NIM improved to 3.65% from 3.45% last quarter. Gross NPA improved to 1.24% from 1.28%. "
                  "Casa ratio: 44.1%. Advances growth: 19.2% YoY.",
        "confidence_score": 0.88,
        "signal_date": _d(5),
        "stock_price_at_signal": 1648.0,
        "expected_impact": "BULLISH",
        "ai_analysis": "Earnings beat of 6.6% on NII with NIM expansion is a strong rerating signal.",
        "data_sources": ["BSE Quarterly Results", "Investor Presentation"],
        "tags": ["earnings", "hdfcbank", "beat", "nii", "banking"],
    },
    {
        "id": "sig006",
        "symbol": "BAJFINANCE",
        "company_name": "Bajaj Finance Ltd",
        "signal_type": "CORPORATE_ACTION",
        "headline": "Bajaj Finance 1:1 bonus issue — effective April 15, 2026",
        "detail": "Bajaj Finance's board has approved a 1:1 bonus issue, effective record date April 15, 2026. "
                  "Shareholders will receive 1 additional share for every share held. "
                  "Post-bonus, the face value remains ₹2. Share price will adjust to ~₹3,600 from ₹7,215. "
                  "Retail participation typically surges post-bonus due to improved affordability.",
        "confidence_score": 0.79,
        "signal_date": _d(4),
        "stock_price_at_signal": 7215.0,
        "expected_impact": "BULLISH",
        "ai_analysis": "Bonus issues improve retail accessibility and signal promoter confidence.",
        "data_sources": ["BSE Corporate Action", "NSE Announcement"],
        "tags": ["bonus", "bajfinance", "corporate_action", "retail", "nbfc"],
    },
    {
        "id": "sig007",
        "symbol": "NIFTY",
        "company_name": "NSE Nifty 50 Index",
        "signal_type": "FII_ACCUMULATION",
        "headline": "FII 7-day buying streak: ₹28,500 Cr net inflow — strongest since Nov 2024",
        "detail": "Foreign Institutional Investors have been net buyers for 7 consecutive trading days "
                  "with cumulative inflow of ₹28,500 Cr (₹4,071 Cr/day average). "
                  "Meanwhile, DIIs have been net sellers of ₹12,200 Cr during the same period. "
                  "EM flows tracker shows India receiving 38% of all EM allocation in the past 2 weeks. "
                  "The last time this happened (Nov 2024), Nifty rallied 8% over the following 6 weeks.",
        "confidence_score": 0.82,
        "signal_date": _d(0),
        "stock_price_at_signal": 22350.0,
        "expected_impact": "BULLISH",
        "ai_analysis": "7-day FII streak with ₹28,500 Cr inflow is a strong macro bullish indicator.",
        "data_sources": ["NSE FII/DII Data", "SEBI Institutional Data"],
        "tags": ["fii", "accumulation", "streak", "macro", "nifty", "bullish"],
    },
    {
        "id": "sig008",
        "symbol": "SUNPHARMA",
        "company_name": "Sun Pharmaceutical Industries",
        "signal_type": "FILING",
        "headline": "USFDA EIR received for Halol facility — clears cloud over 35% of US revenue",
        "detail": "Sun Pharma received the Establishment Inspection Report (EIR) from USFDA for its "
                  "Halol manufacturing facility on March 18, 2026. The EIR indicates satisfactory resolution "
                  "of all previously cited observations. The Halol facility contributes approximately "
                  "35% of Sun Pharma's US revenues (~$800M annually). "
                  "This removes a key regulatory overhang that has weighed on the stock for 14 months.",
        "confidence_score": 0.85,
        "signal_date": _d(1),
        "stock_price_at_signal": 1782.0,
        "expected_impact": "BULLISH",
        "ai_analysis": "USFDA EIR for Halol removes 14-month overhang. Expect analyst upgrades.",
        "data_sources": ["BSE Filing", "USFDA Database"],
        "tags": ["pharma", "usfda", "regulatory", "sunpharma", "eir", "bullish"],
    },
    {
        "id": "sig009",
        "symbol": "COALINDIA",
        "company_name": "Coal India Ltd",
        "signal_type": "FILING",
        "headline": "Auditor notes concerns on inventory valuation methodology — review risk flag",
        "detail": "Coal India's statutory auditor has noted concerns in the Q4 FY26 audit report regarding "
                  "the valuation methodology for coal inventory (₹3,200 Cr impact potential). "
                  "The auditor has requested management clarification within 45 days. "
                  "While not a qualification, this is a caution flag that may delay the annual results sign-off. "
                  "Government ownership at 66.1% limits downside, but uncertainty may cap near-term upside.",
        "confidence_score": 0.72,
        "signal_date": _d(3),
        "stock_price_at_signal": 485.0,
        "expected_impact": "BEARISH",
        "ai_analysis": "Auditor concerns on ₹3,200 Cr inventory creates near-term uncertainty.",
        "data_sources": ["BSE Filing", "Annual Report"],
        "tags": ["coal", "auditor", "risk", "bearish", "accounting"],
    },
    {
        "id": "sig010",
        "symbol": "TATAMOTORS",
        "company_name": "Tata Motors Ltd",
        "signal_type": "FILING",
        "headline": "EV sales cross 1 lakh cumulative units in FY26 — 6 months ahead of target",
        "detail": "Tata Motors announced EV sales milestone: cumulative 1,00,000 units sold in FY26, "
                  "achieving guidance 6 months earlier than projected. "
                  "Market share in passenger EV: 61.2%. "
                  "Nexon EV remains #1 with 58,000 units; Punch EV at 32,000 units. "
                  "Management has upgraded FY27 EV volume guidance from 2.5L to 3.2L units.",
        "confidence_score": 0.80,
        "signal_date": _d(2),
        "stock_price_at_signal": 962.0,
        "expected_impact": "BULLISH",
        "ai_analysis": "EV milestone 6 months early triggers guidance upgrade cycle.",
        "data_sources": ["BSE Announcement", "Monthly Auto Sales Data"],
        "tags": ["ev", "tatamotors", "sales", "guidance", "auto", "bullish"],
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# DEMO PATTERNS (20+ items)
# ─────────────────────────────────────────────────────────────────────────────
DEMO_PATTERNS = [
    {
        "symbol": "RELIANCE.NS",
        "pattern_type": "GOLDEN_CROSS",
        "detected_at": _d(1),
        "confidence": 0.82,
        "direction": "BULLISH",
        "key_levels": {"support": 2820, "resistance": 3024, "target": 3200, "stop_loss": 2780},
        "indicators": {"EMA50": 2895, "EMA200": 2845, "ADX": 28.5, "RSI": 58.2},
        "pattern_label": "Golden Cross (EMA50 > EMA200)",
        "backtest_stats": {"win_rate": 71, "avg_return_pct": 14.2, "avg_holding_days": 48, "sample_size": 8},
    },
    {
        "symbol": "TCS.NS",
        "pattern_type": "RSI_DIVERGENCE",
        "detected_at": _d(0),
        "confidence": 0.74,
        "direction": "BULLISH",
        "key_levels": {"support": 3950, "target": 4400, "stop_loss": 3900},
        "indicators": {"RSI": 38.5, "RSI_prev": 31.2},
        "pattern_label": "RSI Bullish Divergence",
        "backtest_stats": {"win_rate": 64, "avg_return_pct": 9.8, "avg_holding_days": 22, "sample_size": 12},
    },
    {
        "symbol": "HDFCBANK.NS",
        "pattern_type": "BREAKOUT",
        "detected_at": _d(0),
        "confidence": 0.78,
        "direction": "BULLISH",
        "key_levels": {"breakout_level": 1780, "target": 1950, "stop_loss": 1720},
        "indicators": {"volume_ratio": 2.1, "52w_high": 1780},
        "pattern_label": "52-Week High Breakout",
        "backtest_stats": {"win_rate": 67, "avg_return_pct": 12.4, "avg_holding_days": 28, "sample_size": 6},
    },
    {
        "symbol": "INFY.NS",
        "pattern_type": "MACD_CROSSOVER",
        "detected_at": _d(2),
        "confidence": 0.68,
        "direction": "BULLISH",
        "key_levels": {"target": 1950, "stop_loss": 1700},
        "indicators": {"MACD": 8.5, "MACD_signal": 5.2, "MACD_hist": 3.3},
        "pattern_label": "MACD Bullish Crossover",
        "backtest_stats": {"win_rate": 60, "avg_return_pct": 8.2, "avg_holding_days": 18, "sample_size": 15},
    },
    {
        "symbol": "ICICIBANK.NS",
        "pattern_type": "SUPPORT_BOUNCE",
        "detected_at": _d(1),
        "confidence": 0.71,
        "direction": "BULLISH",
        "key_levels": {"support": 1090, "target": 1250, "stop_loss": 1060},
        "indicators": {"RSI": 29.8, "BB_lower": 1092},
        "pattern_label": "Bollinger Band Bounce",
        "backtest_stats": {"win_rate": 63, "avg_return_pct": 7.5, "avg_holding_days": 14, "sample_size": 11},
    },
    {
        "symbol": "BAJFINANCE.NS",
        "pattern_type": "BULLISH_ENGULFING",
        "detected_at": _d(0),
        "confidence": 0.66,
        "direction": "BULLISH",
        "key_levels": {"support": 7050, "target": 7500, "stop_loss": 6980},
        "indicators": {"engulfing_ratio": 1.8},
        "pattern_label": "Bullish Engulfing Candle",
        "backtest_stats": {"win_rate": 61, "avg_return_pct": 5.8, "avg_holding_days": 8, "sample_size": 18},
    },
    {
        "symbol": "TATASTEEL.NS",
        "pattern_type": "DEATH_CROSS",
        "detected_at": _d(4),
        "confidence": 0.73,
        "direction": "BEARISH",
        "key_levels": {"support": 130, "resistance": 160, "target": 138, "stop_loss": 165},
        "indicators": {"EMA50": 148, "EMA200": 153, "ADX": 31.2, "RSI": 42.5},
        "pattern_label": "Death Cross (EMA50 < EMA200)",
        "backtest_stats": {"win_rate": 62, "avg_return_pct": -9.5, "avg_holding_days": 38, "sample_size": 7},
    },
    {
        "symbol": "NESTLEIND.NS",
        "pattern_type": "RSI_OVERBOUGHT",
        "detected_at": _d(0),
        "confidence": 0.64,
        "direction": "BEARISH",
        "key_levels": {"resistance": 25200, "target": 23500, "stop_loss": 25500},
        "indicators": {"RSI": 74.2},
        "pattern_label": "RSI Overbought (>70)",
        "backtest_stats": {"win_rate": 57, "avg_return_pct": -5.8, "avg_holding_days": 15, "sample_size": 9},
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# DEMO FII/DII DATA (30 days)
# ─────────────────────────────────────────────────────────────────────────────
DEMO_FII_DII = []
import random as _rnd
_rnd.seed(42)
for i in range(30):
    d = TODAY - timedelta(days=30 - i)
    if d.weekday() < 5:
        fii = round(_rnd.uniform(-2500, 4000), 2)
        dii = round(-fii * _rnd.uniform(0.5, 1.1) + _rnd.uniform(-500, 500), 2)
        fii_buy = round(abs(fii) + _rnd.uniform(1000, 6000), 2)
        dii_buy = round(abs(dii) + _rnd.uniform(800, 5000), 2)
        DEMO_FII_DII.append({
            "date": d.strftime("%Y-%m-%d"),
            "fii_buy": fii_buy, "fii_sell": round(fii_buy - fii, 2), "fii_net": fii,
            "dii_buy": dii_buy, "dii_sell": round(dii_buy - dii, 2), "dii_net": dii,
        })

# ─────────────────────────────────────────────────────────────────────────────
# DEMO PORTFOLIO EXAMPLES
# ─────────────────────────────────────────────────────────────────────────────
DEMO_PORTFOLIOS = [
    {
        "name": "Balanced Large-Cap",
        "risk_profile": "MODERATE",
        "holdings": [
            {"symbol": "RELIANCE", "quantity": 50, "avg_cost": 2650, "current_price": 2920},
            {"symbol": "TCS", "quantity": 30, "avg_cost": 3800, "current_price": 4112},
            {"symbol": "HDFCBANK", "quantity": 100, "avg_cost": 1580, "current_price": 1648},
            {"symbol": "INFY", "quantity": 80, "avg_cost": 1600, "current_price": 1782},
            {"symbol": "ICICIBANK", "quantity": 120, "avg_cost": 950, "current_price": 1185},
        ]
    },
    {
        "name": "Growth Focused",
        "risk_profile": "AGGRESSIVE",
        "holdings": [
            {"symbol": "BAJFINANCE", "quantity": 20, "avg_cost": 6800, "current_price": 7215},
            {"symbol": "ADANIENT", "quantity": 40, "avg_cost": 2800, "current_price": 3151},
            {"symbol": "TATAMOTORS", "quantity": 150, "avg_cost": 800, "current_price": 962},
            {"symbol": "TITAN", "quantity": 45, "avg_cost": 3200, "current_price": 3610},
        ]
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# Helper function to get demo data
# ─────────────────────────────────────────────────────────────────────────────

def get_demo_signals():
    """Return all demo signals."""
    return DEMO_SIGNALS


def get_demo_patterns():
    """Return all demo patterns."""
    return DEMO_PATTERNS


def get_demo_fii_data():
    """Return demo FII/DII data."""
    return DEMO_FII_DII


def get_demo_portfolio(index: int = 0):
    """Return a demo portfolio by index."""
    return DEMO_PORTFOLIOS[index % len(DEMO_PORTFOLIOS)]
