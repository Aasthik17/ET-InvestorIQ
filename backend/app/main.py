"""
ET InvestorIQ — FastAPI Main Application
Central app configuration with all modules registered.
"""

import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import os

from app.config import settings
from app.modules.opportunity_radar.router import router as radar_router
from app.modules.chart_pattern.router import router as charts_router
from app.modules.market_chat.router import router as chat_router
from app.modules.video_engine.router import router as video_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ─── Startup / Shutdown lifecycle ─────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    logger.info("ET InvestorIQ API starting up...")
    logger.info(f"Mock mode: {settings.mock_mode}")

    # Pre-warm cache with top 10 stocks
    try:
        from app.services import data_service
        from app.services.cache_service import cache
        import asyncio

        top_10 = settings.nse_top_50[:10]
        logger.info(f"Pre-warming cache for {len(top_10)} stocks...")
        results = await asyncio.gather(
            *[data_service.get_fundamentals(sym) for sym in top_10],
            return_exceptions=True,
        )
        ok_count = sum(1 for r in results if not isinstance(r, Exception))
        logger.info(f"Cache pre-warm complete: {ok_count}/{len(top_10)} stocks loaded")
    except Exception as e:
        logger.warning(f"Cache pre-warm failed (non-critical): {e}")

    yield

    logger.info("ET InvestorIQ API shutting down.")


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
    allow_origins=settings.cors_origins_list + ["*"],  # Allow all in development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Request logging middleware ───────────────────────────────────────────────

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests with timing."""
    start = time.time()
    try:
        response = await call_next(request)
    except Exception as e:
        logger.error(f"Unhandled error in {request.method} {request.url.path}: {e}")
        raise
    elapsed_ms = round((time.time() - start) * 1000)
    if request.url.path not in ["/api/health", "/docs", "/openapi.json"]:
        logger.info(f"{request.method} {request.url.path} → {response.status_code} ({elapsed_ms}ms)")
    return response


# ─── Global exception handler ─────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Return JSON error for all unhandled exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "detail": str(exc),
            "path": str(request.url.path),
            "timestamp": datetime.now().isoformat(),
        }
    )


# ─── Register module routers ──────────────────────────────────────────────────

app.include_router(radar_router)
app.include_router(charts_router)
app.include_router(chat_router)
app.include_router(video_router)

# ─── Static files for generated videos ───────────────────────────────────────

video_dir = settings.video_output_dir
os.makedirs(video_dir, exist_ok=True)
app.mount("/videos", StaticFiles(directory=video_dir), name="videos")


# ─── Core API Endpoints ───────────────────────────────────────────────────────

@app.get("/api/health", tags=["System"])
async def health_check():
    """Health check endpoint for load balancers and monitoring."""
    return {
        "status": "healthy",
        "service": "ET InvestorIQ API",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "mock_mode": settings.mock_mode,
    }


@app.get("/api/market/overview", tags=["Market"])
async def market_overview():
    """
    Combined market snapshot endpoint for the Dashboard.
    Returns Nifty50, Sensex, top movers, FII flow, market breadth, and sentiment.
    Cached for 5 minutes.
    """
    from app.services import data_service
    from app.services.cache_service import cache

    cached = cache.get("market_overview")
    if cached:
        return cached

    overview = await data_service.get_market_overview()
    cache.set("market_overview", overview, ttl_seconds=300)
    return overview


@app.get("/api/market/sectors", tags=["Market"])
async def sector_performance():
    """Get sector performance data for all major NSE sectors."""
    from app.services import data_service
    from app.services.cache_service import cache

    cached = cache.get("sector_performance")
    if cached:
        return cached

    data = await data_service.get_sector_performance()
    cache.set("sector_performance", data, ttl_seconds=1800)
    return data


@app.get("/api/market/ipo", tags=["Market"])
async def ipo_data():
    """Get upcoming and recent IPO data."""
    from app.services import data_service
    return await data_service.get_ipo_data()


@app.get("/api/market/stock/{symbol}", tags=["Market"])
async def stock_fundamentals(symbol: str):
    """Get fundamental data for a specific stock."""
    from app.services import data_service
    from app.services.cache_service import cache

    sym = symbol.upper()
    if "." not in sym:
        sym += ".NS"

    cached = cache.get_fundamentals(sym)
    if cached:
        return cached

    data = await data_service.get_fundamentals(sym)
    cache.cache_fundamentals(sym, data)
    return data


@app.get("/api/market/news/{symbol}", tags=["Market"])
async def stock_news(symbol: str):
    """Get recent news for a stock with sentiment analysis."""
    from app.services import data_service
    from app.services.cache_service import cache

    sym = symbol.upper()
    if "." not in sym:
        sym += ".NS"

    cached = cache.get_news(sym)
    if cached:
        return cached

    data = await data_service.get_news(sym)
    cache.cache_news(sym, data)
    return data


@app.get("/", tags=["System"])
async def root():
    """API root with quick start info."""
    return {
        "message": "Welcome to ET InvestorIQ API",
        "docs": "/docs",
        "health": "/api/health",
        "modules": {
            "opportunity_radar": "/api/radar/signals",
            "chart_intelligence": "/api/charts/scan/{symbol}",
            "market_chat": "/api/chat/message",
            "video_engine": "/api/video/generate",
        }
    }
