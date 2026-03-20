"""
ET InvestorIQ — Live Prices WebSocket Router
Streams live index and stock prices to connected frontend clients.

ENDPOINT 1: GET /ws/prices
  Pushes index quotes (Nifty50, Sensex, Bank Nifty, VIX) + top movers
  every 4 seconds. Dashboard connects here for the ticker tape.

ENDPOINT 2: GET /ws/stock/{symbol}
  Pushes a single stock's live quote every 5 seconds.
  ChartIntelligence connects here to overlay a live price line.
"""

import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.data_service import get_index_quotes, get_stock_quote, get_top_movers

router = APIRouter(tags=["Live Prices"])
logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages all active WebSocket connections."""

    def __init__(self):
        self.index_connections: list[WebSocket] = []
        self.stock_connections: dict[str, list[WebSocket]] = {}

    async def connect_index(self, ws: WebSocket):
        await ws.accept()
        self.index_connections.append(ws)
        logger.info(f"Index WS connected. Total: {len(self.index_connections)}")

    def disconnect_index(self, ws: WebSocket):
        try:
            self.index_connections.remove(ws)
        except ValueError:
            pass

    async def connect_stock(self, ws: WebSocket, symbol: str):
        await ws.accept()
        self.stock_connections.setdefault(symbol, []).append(ws)
        logger.info(f"Stock WS connected for {symbol}.")

    def disconnect_stock(self, ws: WebSocket, symbol: str):
        try:
            self.stock_connections.get(symbol, []).remove(ws)
        except ValueError:
            pass

    async def _safe_send(self, ws: WebSocket, data: dict) -> bool:
        """Return False if the connection is dead."""
        try:
            await ws.send_json(data)
            return True
        except Exception:
            return False


manager = ConnectionManager()


@router.websocket("/ws/prices")
async def websocket_index_prices(websocket: WebSocket):
    """
    Stream live index prices + top movers to the Dashboard ticker tape.
    Pushes every 4 seconds. Auto-drops dead connections.
    """
    await manager.connect_index(websocket)
    try:
        while True:
            try:
                indices = await get_index_quotes()
                movers  = await get_top_movers()
                payload = {
                    "type":    "index_update",
                    "indices": indices,
                    "movers":  movers,
                }
                ok = await manager._safe_send(websocket, payload)
                if not ok:
                    break
            except Exception as e:
                logger.warning(f"Index WS push error: {e}")
            await asyncio.sleep(4)
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect_index(websocket)
        logger.info(f"Index WS disconnected. Remaining: {len(manager.index_connections)}")


@router.websocket("/ws/stock/{symbol}")
async def websocket_stock_price(websocket: WebSocket, symbol: str):
    """
    Stream live quote for a single NSE stock.
    symbol: NSE symbol without .NS (e.g., RELIANCE).
    Pushes every 5 seconds.
    """
    sym = symbol.upper()
    await manager.connect_stock(websocket, sym)
    try:
        while True:
            try:
                quote = await get_stock_quote(sym)
                ok = await manager._safe_send(websocket, {
                    "type":  "stock_update",
                    "quote": quote,
                })
                if not ok:
                    break
            except Exception as e:
                logger.warning(f"Stock WS push error for {sym}: {e}")
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect_stock(websocket, sym)
        logger.info(f"Stock WS disconnected for {sym}")
