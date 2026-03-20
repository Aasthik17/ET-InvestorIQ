"""
ET InvestorIQ — NSE Session Manager
Manages authenticated session with NSE India's unofficial API.
NSE requires cookie-based auth obtained by first hitting the homepage.
Session expires after ~10 minutes of inactivity — auto-refreshes.
"""

import asyncio
import logging
from datetime import datetime

try:
    import httpx
except ImportError:
    httpx = None

try:
    from fake_useragent import UserAgent
    _UA_AVAILABLE = True
except ImportError:
    _UA_AVAILABLE = False

try:
    from tenacity import retry, stop_after_attempt, wait_exponential
    _TENACITY_AVAILABLE = True
except ImportError:
    _TENACITY_AVAILABLE = False

logger = logging.getLogger(__name__)

# Default Chrome UA as fallback
_DEFAULT_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


class NSESession:
    """
    Singleton that manages an HTTP session with NSE India's unofficial API.
    NSE requires:
      1. A valid browser-like User-Agent header
      2. A session cookie obtained by first hitting the homepage
      3. Referer: https://www.nseindia.com
    Session expires after ~10 min of inactivity — auto-refreshes every 8 min.
    """

    BASE_URL = "https://www.nseindia.com"
    SESSION_REFRESH_INTERVAL = 480  # 8 minutes (before 10 min NSE expiry)

    NSE_ENDPOINTS = {
        "nifty50":           "/api/equity-stockIndices?index=NIFTY%2050",
        "sensex_next":       "/api/equity-stockIndices?index=NIFTY%20NEXT%2050",
        "banknifty":         "/api/equity-stockIndices?index=NIFTY%20BANK",
        "quote":             "/api/quote-equity?symbol={symbol}",
        "market_status":     "/api/market-status",
        "top_gainers":       "/api/live-analysis-variations?index=gainers",
        "top_losers":        "/api/live-analysis-variations?index=loosers",
        "bulk_deals":        "/api/historical/bulk-deals?from={from_date}&to={to_date}",
        "block_deals":       "/api/historical/block-deals?from={from_date}&to={to_date}",
        "insider_trades":    "/api/corporate-pledgedata?from={from_date}&to={to_date}&category=insider",
        "corporate_filings": "/api/corporate-announcements?index=equities&from_date={from_date}&to_date={to_date}",
        "fii_dii":           "/api/fiidiiTradeReact",
        "ipo_current":       "/api/public-IPO?status=current",
        "ipo_upcoming":      "/api/public-IPO?status=upcoming",
        "ipo_listed":        "/api/public-IPO?status=listed",
    }

    _instance = None
    _lock = None  # Created lazily to avoid event loop issues

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    async def initialize(self):
        """Call once on app startup to establish session."""
        if self._initialized:
            return
        if self.__class__._lock is None:
            self.__class__._lock = asyncio.Lock()

        if _UA_AVAILABLE:
            try:
                ua = UserAgent()
                user_agent = ua.chrome
            except Exception:
                user_agent = _DEFAULT_UA
        else:
            user_agent = _DEFAULT_UA

        self._headers = {
            "User-Agent": user_agent,
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Referer": "https://www.nseindia.com/",
            "X-Requested-With": "XMLHttpRequest",
        }

        if httpx:
            self._client = httpx.AsyncClient(
                headers=self._headers,
                timeout=15.0,
                follow_redirects=True,
            )
        else:
            self._client = None

        self._semaphore = asyncio.Semaphore(1)  # One NSE request at a time
        self._session_established = False
        self._last_refresh = None

        await self._establish_session()
        self._initialized = True

    async def _establish_session(self):
        """Hit NSE homepage to obtain session cookies."""
        if not self._client:
            logger.warning("httpx not available; NSE session skipped")
            return
        try:
            resp = await self._client.get(self.BASE_URL + "/")
            resp.raise_for_status()
            # Hit a secondary page to strengthen cookie
            await asyncio.sleep(1.5)
            await self._client.get(self.BASE_URL + "/market-data/live-equity-market")
            self._session_established = True
            self._last_refresh = datetime.now()
            logger.info("NSE session established successfully")
        except Exception as e:
            logger.warning(f"NSE session establishment failed: {e}. Will use fallbacks.")
            self._session_established = False

    async def _maybe_refresh_session(self):
        """Refresh session if it's about to expire."""
        if self._last_refresh is None:
            await self._establish_session()
            return
        age = (datetime.now() - self._last_refresh).seconds
        if age > self.SESSION_REFRESH_INTERVAL:
            await self._establish_session()

    async def get(self, endpoint_key: str, **format_kwargs) -> dict:
        """
        Make an authenticated GET request to an NSE endpoint.
        Handles session refresh, rate limiting (1 req/2 sec), and retries.
        Returns empty dict on irrecoverable failure (never raises to caller).
        """
        if not self._client or not self._session_established:
            return {}

        async with self._semaphore:
            await self._maybe_refresh_session()
            url = self.BASE_URL + self.NSE_ENDPOINTS[endpoint_key].format(**format_kwargs)

            for attempt in range(3):
                try:
                    resp = await self._client.get(url)
                    resp.raise_for_status()
                    await asyncio.sleep(2)  # NSE rate limit
                    return resp.json()
                except Exception as e:
                    if attempt == 2:
                        logger.error(f"NSE API failed for {endpoint_key} after 3 attempts: {e}")
                        return {}
                    wait = 2 ** attempt
                    logger.warning(f"NSE {endpoint_key} attempt {attempt+1} failed: {e}. Retrying in {wait}s")
                    await asyncio.sleep(wait)
                    # Try refreshing session on auth errors
                    if hasattr(e, 'response') and getattr(e.response, 'status_code', 0) == 401:
                        await self._establish_session()

        return {}

    async def close(self):
        """Close the HTTP client — call on app shutdown."""
        if self._client:
            await self._client.aclose()
            self._initialized = False


# Singleton instance
nse = NSESession()
