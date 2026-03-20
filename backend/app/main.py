"""
ET InvestorIQ — FastAPI Main Application
Central app configuration, module registration, APScheduler background jobs.
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import os

from app.config import settings
from app.modules.opportunity_radar.router import router as radar_router
from app.modules.chart_pattern.router    import router as charts_router
from app.modules.market_chat.router      import router as chat_router
from app.modules.video_engine.router     import router as video_router
from app.modules.live_prices.router      import router as live_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ─── APScheduler background jobs ─────────────────────────────────────────────

try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.interval  import IntervalTrigger
    _SCHEDULER_AVAILABLE = True
except ImportError:
    _SCHEDULER_AVAILABLE = False
    logger.warning("APScheduler not installed. Background refresh disabled.")

scheduler = AsyncIOScheduler(timezone="Asia/Kolkata") if _SCHEDULER_AVAILABLE else None


async def _refresh_prices():
    """Every 30 seconds: refresh live index quotes and top movers in cache."""
    try:
        from app.services.data_service import get_index_quotes, get_top_movers
        await asyncio.gather(get_index_quotes(), get_top_movers(), return_exceptions=True)
    except Exception as e:
        logger.warning(f"Scheduler refresh_prices failed: {e}")


async def _refresh_radar():
    """Every 5 minutes: refresh bulk deals, insider trades, filings, signals."""
    try:
        from app.services.data_service import (
            get_bulk_block_deals, get_insider_trades, get_corporate_filings
        )
        await asyncio.gather(
            get_bulk_block_deals(),
            get_insider_trades(),
            get_corporate_filings(),
            return_exceptions=True,
        )
        # Also trigger signal engine refresh
        try:
            from app.modules.opportunity_radar.service import refresh_signals
            await refresh_signals()
        except Exception as e:
            logger.warning(f"Signal engine refresh failed: {e}")
    except Exception as e:
        logger.warning(f"Scheduler refresh_radar failed: {e}")


async def _refresh_batch():
    """Every hour: refresh slow-changing data (FII/DII, IPOs, sectors)."""
    try:
        from app.services.data_service import (
            get_fii_dii_data, get_ipo_data, get_sector_performance
        )
        await asyncio.gather(
            get_fii_dii_data(),
            get_ipo_data(),
            get_sector_performance(),
            return_exceptions=True,
        )
    except Exception as e:
        logger.warning(f"Scheduler refresh_batch failed: {e}")


# ─── Startup / Shutdown lifecycle ─────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("ET InvestorIQ API starting up…")
    logger.info(f"Mock mode: {settings.mock_mode}")

    # Initialize NSE session
    try:
        from app.services.nse_session import nse
        await nse.initialize()
        logger.info("NSE session initialized")
    except Exception as e:
        logger.warning(f"NSE session init failed (non-critical): {e}")

    # Pre-warm cache on startup (best-effort)
    try:
        await asyncio.gather(
            _refresh_prices(),
            _refresh_batch(),
            return_exceptions=True,
        )
        await _refresh_radar()
        logger.info("Cache pre-warm complete")
    except Exception as e:
        logger.warning(f"Cache pre-warm failed (non-critical): {e}")

    # Start APScheduler
    if scheduler and _SCHEDULER_AVAILABLE:
        scheduler.add_job(_refresh_prices, IntervalTrigger(seconds=30),  id="prices",  replace_existing=True)
        scheduler.add_job(_refresh_radar,  IntervalTrigger(minutes=5),   id="radar",   replace_existing=True)
        scheduler.add_job(_refresh_batch,  IntervalTrigger(hours=1),     id="batch",   replace_existing=True)
        scheduler.start()
        logger.info("APScheduler started (prices every 30s, radar every 5m, batch every 1h)")

    yield

    # Shutdown
    logger.info("ET InvestorIQ API shutting down…")
    if scheduler and _SCHEDULER_AVAILABLE and scheduler.running:
        scheduler.shutdown(wait=False)
    try:
        from app.services.nse_session import nse
        await nse.close()
    except Exception:
        pass


# ─── App initialization ───────────────────────────────────────────────────────

app = FastAPI(
    title="ET InvestorIQ API",
    description=(
        "AI-powered investment intelligence platform for Indian equity markets. "
        "Built for the Economic Times Gen AI Hackathon 2026."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ─── CORS Middleware ──────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Request logging middleware ───────────────────────────────────────────────

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    try:
        response = await call_next(request)
    except Exception as e:
        logger.error(f"Unhandled error in {request.method} {request.url.path}: {e}")
        raise
    elapsed_ms = round((time.time() - start) * 1000)
    skip = ["/api/health", "/docs", "/openapi.json", "/redoc"]
    if request.url.path not in skip:
        logger.info(f"{request.method} {request.url.path} → {response.status_code} ({elapsed_ms}ms)")
    return response

# ─── Global exception handler ─────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error":     "Internal server error",
            "detail":    str(exc),
            "path":      str(request.url.path),
            "timestamp": datetime.now().isoformat(),
        }
    )

# ─── Register module routers ──────────────────────────────────────────────────

app.include_router(radar_router)
app.include_router(charts_router)
app.include_router(chat_router)
app.include_router(video_router)
app.include_router(live_router)  # WebSocket price streaming

# ─── Static files for generated videos ───────────────────────────────────────

video_dir = settings.video_output_dir
os.makedirs(video_dir, exist_ok=True)
app.mount("/videos", StaticFiles(directory=video_dir), name="videos")


# ─── Core API Endpoints ───────────────────────────────────────────────────────

@app.get("/api/health", tags=["System"])
async def health_check():
    return {
        "status":    "healthy",
        "service":   "ET InvestorIQ API",
        "version":   "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "mock_mode": settings.mock_mode,
    }


@app.get("/api/market/overview", tags=["Market"])
async def market_overview():
    """
    Combined market snapshot for the Dashboard.
    All sub-data is pre-warmed by APScheduler, so response < 50ms typical.
    Aggregates: indices, movers, FII/DII (7d), sectors, IPO pipeline, breadth.
    """
    from app.services.data_service  import get_market_overview
    from app.services.cache_service import cache

    cached = cache.get("market_overview_full")
    if cached:
        return cached

    overview = await get_market_overview()
    cache.set("market_overview_full", overview, ttl_seconds=30)
    return overview


@app.get("/api/market/sectors", tags=["Market"])
async def sector_performance():
    from app.services.data_service import get_sector_performance
    return await get_sector_performance()


@app.get("/api/market/ipo", tags=["Market"])
async def ipo_data():
    from app.services.data_service import get_ipo_data
    return await get_ipo_data()


@app.get("/api/market/stock/{symbol}", tags=["Market"])
async def stock_details(symbol: str):
    """Fundamental data + live quote for a single NSE stock."""
    from app.services.data_service import get_fundamentals, get_stock_quote
    sym = symbol.upper().replace(".NS", "")
    fundamentals, quote = await asyncio.gather(
        get_fundamentals(sym),
        get_stock_quote(sym),
        return_exceptions=True,
    )
    return {
        "symbol":       sym,
        "fundamentals": fundamentals if not isinstance(fundamentals, Exception) else {},
        "quote":        quote        if not isinstance(quote, Exception) else {},
    }


@app.get("/api/market/news/{symbol}", tags=["Market"])
async def stock_news(symbol: str):
    from app.services.data_service import get_news
    return await get_news(symbol.upper().replace(".NS", ""))


@app.get("/api/market/indices", tags=["Market"])
async def index_quotes():
    """Live index quotes (Nifty 50, Sensex, Bank Nifty, VIX). Cached 30s."""
    from app.services.data_service import get_index_quotes
    return await get_index_quotes()


@app.get("/api/market/movers", tags=["Market"])
async def top_movers():
    """Top 10 gainers and losers. Cached 60s."""
    from app.services.data_service import get_top_movers
    return await get_top_movers()


@app.get("/", tags=["System"])
async def root():
    return {
        "message": "Welcome to ET InvestorIQ API",
        "docs":    "/docs",
        "health":  "/api/health",
        "ws": {
            "index_prices": "/ws/prices",
            "stock_price":  "/ws/stock/{symbol}",
        },
        "modules": {
            "opportunity_radar":  "/api/radar/signals",
            "chart_intelligence": "/api/charts/ohlcv/{symbol}",
            "market_chat":        "/api/chat/message",
            "video_engine":       "/api/video/generate",
        },
    }
