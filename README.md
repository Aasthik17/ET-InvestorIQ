# ET InvestorIQ — AI Investment Intelligence Platform

> **Economic Times Gen AI Hackathon 2026**

ET InvestorIQ is a production-grade AI investment intelligence platform that transforms raw NSE/BSE market data into actionable decisions for India's 14 crore+ demat account holders.

---

## Modules

| Module | Description |
|---|---|
| 🎯 **Opportunity Radar** | Insider trades, bulk deals, FII accumulation, corporate filings — all scored by Claude AI |
| 📈 **Chart Intelligence** | 15+ technical patterns (Golden Cross, RSI divergence, MACD, Bollinger Bands, candlesticks) with backtesting |
| 💬 **Market Chat** | Portfolio-aware AI chat with tool-augmented Claude (stock quotes, comparison, technical levels) |
| 🎬 **Video Engine** | AI-narrated market videos: Market Wrap, Sector Rotation, FII Flow, Race Chart, IPO Tracker |

---

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 20+
- Anthropic API key

### 1. Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
uvicorn app.main:app --reload --port 8000
```

Backend: **http://localhost:8000** · API docs: **http://localhost:8000/docs**

### 2. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Frontend: **http://localhost:5173**

---

## Mock Mode (Offline Demo)

Set `MOCK_MODE=true` in `backend/.env` to use realistic mock data without live API access. The platform works fully offline — perfect for demos.

---

## Environment Variables

```env
ANTHROPIC_API_KEY=sk-ant-...   # Required for AI features
MOCK_MODE=false                 # true for offline demo
REDIS_URL=redis://localhost:6379/0
VIDEO_OUTPUT_DIR=./generated_videos
CORS_ORIGINS=http://localhost:5173
```

---

## Docker Deployment

```bash
cp backend/.env.example backend/.env
# Add ANTHROPIC_API_KEY to backend/.env
docker-compose up --build
# Frontend: http://localhost:5173
# Backend: http://localhost:8000
```

---

## Tech Stack

**Backend:** Python 3.11 · FastAPI · Anthropic Claude Sonnet · yfinance · pandas · ta · matplotlib · fakeredis

**Frontend:** React 18 · Vite · TailwindCSS · Recharts · Framer Motion

**Infrastructure:** Docker · Nginx · Redis

---

## API Reference

| Endpoint | Description |
|---|---|
| `GET /api/health` | Health check |
| `GET /api/market/overview` | Market snapshot (Nifty, Sensex, FII) |
| `GET /api/radar/signals` | Opportunity radar signals |
| `GET /api/charts/scan/{symbol}` | Chart pattern scan |
| `GET /api/charts/ohlcv/{symbol}` | OHLCV candlestick data |
| `POST /api/chat/message` | AI chat |
| `POST /api/chat/stream` | Streaming chat (SSE) |
| `POST /api/video/generate` | Generate market video |
| `GET /api/video/job/{job_id}` | Poll video job status |
