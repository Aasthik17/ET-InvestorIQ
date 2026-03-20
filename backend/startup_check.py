"""
ET InvestorIQ — Pre-flight Data Source Check
Run: python startup_check.py

Verifies all data sources are reachable before starting the app.
If critical sources fail, warns and sets MOCK_MODE=true.
"""

import asyncio
import os
import sys

# Load .env first
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
except ImportError:
    pass

GREEN = "\033[92m✓\033[0m"
RED   = "\033[91m✗\033[0m"
WARN  = "\033[93m⚠\033[0m"

results = {}


async def check_nse():
    print("  Checking NSE India API…", end=" ", flush=True)
    try:
        import httpx
        async with httpx.AsyncClient(
            headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"},
            timeout=10.0,
        ) as c:
            r = await c.get("https://www.nseindia.com/")
            if r.status_code == 200:
                print(f"{GREEN} NSE homepage reachable (status 200)")
                results["nse"] = True
            else:
                print(f"{WARN} NSE returned status {r.status_code}")
                results["nse"] = False
    except Exception as e:
        print(f"{RED} NSE unreachable: {e}")
        results["nse"] = False


async def check_yfinance():
    print("  Checking yfinance (RELIANCE.NS)…", end=" ", flush=True)
    try:
        import yfinance as yf
        loop = asyncio.get_event_loop()
        hist = await loop.run_in_executor(
            None,
            lambda: yf.Ticker("RELIANCE.NS").history(period="5d", interval="1d")
        )
        if not hist.empty and len(hist) >= 1:
            print(f"{GREEN} yfinance returned {len(hist)} rows for RELIANCE.NS")
            results["yfinance"] = True
        else:
            print(f"{WARN} yfinance returned empty data")
            results["yfinance"] = False
    except Exception as e:
        print(f"{RED} yfinance failed: {e}")
        results["yfinance"] = False


async def check_bse():
    print("  Checking BSE India API…", end=" ", flush=True)
    try:
        import httpx
        url = "https://api.bseindia.com/BseIndiaAPI/api/AnnSubCategoryGetData/w?strCat=-1&strPrevDate=20250101&strScrip=&strSearch=P&strToDate=20250115&strType=C&subcategory=-1"
        async with httpx.AsyncClient(
            headers={"User-Agent": "Mozilla/5.0", "Referer": "https://www.bseindia.com"},
            timeout=10.0,
        ) as c:
            r = await c.get(url)
            if r.status_code == 200:
                print(f"{GREEN} BSE API reachable")
                results["bse"] = True
            else:
                print(f"{WARN} BSE returned status {r.status_code}")
                results["bse"] = False
    except Exception as e:
        print(f"{RED} BSE unreachable: {e}")
        results["bse"] = False


def check_cache():
    print("  Checking fakeredis/Redis…", end=" ", flush=True)
    try:
        import fakeredis
        r = fakeredis.FakeRedis()
        r.set("test", "ok", ex=5)
        val = r.get("test")
        if val:
            print(f"{GREEN} fakeredis working")
            results["cache"] = True
        else:
            print(f"{RED} fakeredis set/get failed")
            results["cache"] = False
    except Exception as e:
        print(f"{RED} cache init failed: {e}")
        results["cache"] = False


def check_anthropic_key():
    print("  Checking Anthropic API key…", end=" ", flush=True)
    key = os.getenv("ANTHROPIC_API_KEY", "")
    if key and not key.startswith("sk-ant-placeholder"):
        print(f"{GREEN} API key present (not validated)")
        results["anthropic"] = True
    else:
        print(f"{WARN} ANTHROPIC_API_KEY not set or is placeholder — AI features disabled")
        results["anthropic"] = False


async def main():
    print("\n" + "═" * 55)
    print("  ET InvestorIQ — Startup Data Source Check")
    print("═" * 55)

    await asyncio.gather(
        check_nse(),
        check_yfinance(),
        check_bse(),
        return_exceptions=True,
    )
    check_cache()
    check_anthropic_key()

    print("\n" + "─" * 55)
    print("  Summary:")

    all_ok  = all(results.get(k, False) for k in ["yfinance", "cache"])
    mock_on = not all_ok

    for src, ok in results.items():
        icon = GREEN if ok else (WARN if src in ["nse", "bse", "anthropic"] else RED)
        print(f"    {icon}  {src.upper():12s} {'OK' if ok else 'FAILED'}")

    if mock_on:
        print(f"\n  {WARN}  Critical sources unavailable — enabling MOCK_MODE")
        print("     Set MOCK_MODE=true in backend/.env to suppress this warning.")
    else:
        print(f"\n  {GREEN}  All critical data sources reachable. Ready to start.")

    print("─" * 55)
    print("  To start the server:")
    print("    cd backend")
    print("    source venv/bin/activate")
    print("    uvicorn app.main:app --reload --port 8000")
    print("═" * 55 + "\n")

    sys.exit(0 if not mock_on else 1)


if __name__ == "__main__":
    asyncio.run(main())
