"""
Video Pipeline — 4-step autonomous video generation agent.
From raw market data to a playable MP4, zero human editing required.
"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
import subprocess

from .orchestrator import AgentContext, AgentOrchestrator, AgentStep

logger = logging.getLogger(__name__)


def _market_wrap_payload(ctx: AgentContext) -> dict:
    indices = ctx.raw_data.get("indices", {}) or {}
    movers = ctx.raw_data.get("movers", {}) or {}
    fii_dii = ctx.raw_data.get("fii_dii", []) or []

    gainers = movers.get("gainers", [])[:6]
    losers = movers.get("losers", [])[:6]
    advances = sum(1 for item in gainers if float(item.get("change_pct", 0) or 0) >= 0)
    declines = sum(1 for item in losers if float(item.get("change_pct", 0) or 0) < 0)

    nifty = indices.get("nifty50", {}) or {}
    vix = indices.get("vix", {}) or {}
    return {
        "nifty50": {
            "level": float(nifty.get("value", 0) or 0),
            "change_pct": float(nifty.get("change_pct", 0) or 0),
        },
        "top_gainers": gainers,
        "top_losers": losers,
        "market_breadth": {
            "advances": advances or len(gainers),
            "declines": declines or len(losers),
            "unchanged": max(0, 50 - (advances or len(gainers)) - (declines or len(losers))),
        },
        "fii_net_today": float((fii_dii[-1] or {}).get("fii_net", 0) or 0) if fii_dii else 0,
        "vix": float(vix.get("value", 0) or 0),
    }


def _can_run_ffmpeg() -> bool:
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5, check=False)
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


async def step_ingest_market_snapshot(ctx: AgentContext) -> AgentContext:
    """
    Pull the market data required to render a video snapshot.
    """

    from app.services.data_service import (
        get_fii_dii_data,
        get_index_quotes,
        get_ipo_data,
        get_sector_performance,
        get_top_movers,
    )

    indices_task = asyncio.create_task(get_index_quotes())
    movers_task = asyncio.create_task(get_top_movers())
    sectors_task = asyncio.create_task(get_sector_performance())
    fii_task = asyncio.create_task(get_fii_dii_data(days=7))
    ipo_task = asyncio.create_task(get_ipo_data())

    indices, movers, sectors, fii_dii, ipos = await asyncio.gather(
        indices_task,
        movers_task,
        sectors_task,
        fii_task,
        ipo_task,
    )

    ctx.raw_data = {
        "indices": indices if isinstance(indices, dict) else {},
        "movers": movers if isinstance(movers, dict) else {"gainers": [], "losers": []},
        "sectors": sectors if isinstance(sectors, list) else [],
        "fii_dii": fii_dii if isinstance(fii_dii, list) else [],
        "ipos": ipos if isinstance(ipos, dict) else {"current": [], "upcoming": [], "listed": []},
        "video_type": str(ctx.metadata.get("video_type", "MARKET_WRAP")).upper(),
    }
    ctx.metadata["step_0_summary"] = (
        "Ingested live market snapshot: indices, top movers, sector performance, "
        "FII/DII flows, and IPO data."
    )
    return ctx


async def step_generate_narration(ctx: AgentContext) -> AgentContext:
    """
    Ask Claude to generate a narration script for the selected video type.
    """

    from app.services.claude_service import generate_video_narration

    script = await generate_video_narration(
        video_type=ctx.raw_data.get("video_type", "MARKET_WRAP"),
        data=ctx.raw_data,
    )
    ctx.narration = script

    word_count = len(script.split())
    approx_seconds = max(30, int((word_count / 150) * 60)) if word_count else 0
    ctx.metadata["step_1_summary"] = (
        f"Claude generated a {word_count}-word narration script (~{approx_seconds}s runtime)."
    )
    return ctx


async def step_render_charts(ctx: AgentContext) -> AgentContext:
    """
    Render the animation frames for the selected video type.
    """

    from app.config import settings
    from app.modules.video_engine.chart_renderer import (
        render_fii_dii_flow,
        render_ipo_tracker,
        render_market_wrap,
        render_race_chart,
        render_sector_rotation,
    )

    video_type = str(ctx.raw_data.get("video_type", "MARKET_WRAP")).upper()
    output_dir = settings.video_output_dir
    os.makedirs(output_dir, exist_ok=True)
    frames_path = os.path.join(output_dir, f"{ctx.run_id}_frames.mp4")

    market_wrap_data = _market_wrap_payload(ctx)
    sectors = ctx.raw_data.get("sectors", [])
    fii_dii = ctx.raw_data.get("fii_dii", [])
    ipos_dict = ctx.raw_data.get("ipos", {}) or {}
    ipo_items = [
        {**item, "status": str(item.get("status", "LISTED")).title()}
        for status in ("listed", "current", "upcoming")
        for item in ipos_dict.get(status, [])
    ]
    race_symbols = [
        item.get("symbol")
        for item in (ctx.raw_data.get("movers", {}).get("gainers", []) + ctx.raw_data.get("movers", {}).get("losers", []))
        if item.get("symbol")
    ][:8] or ["RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK"]

    loop = asyncio.get_running_loop()

    if video_type == "SECTOR_ROTATION":
        rendered_path = await loop.run_in_executor(None, render_sector_rotation, sectors, frames_path)
    elif video_type == "FII_DII_FLOW":
        rendered_path = await loop.run_in_executor(None, render_fii_dii_flow, fii_dii, frames_path)
    elif video_type in {"BAR_RACE", "RACE_CHART"}:
        rendered_path = await loop.run_in_executor(None, render_race_chart, {}, race_symbols, frames_path)
    elif video_type == "IPO_TRACKER":
        rendered_path = await loop.run_in_executor(None, render_ipo_tracker, ipo_items, frames_path)
    else:
        rendered_path = await loop.run_in_executor(None, render_market_wrap, market_wrap_data, frames_path)

    ctx.metadata["frames_path"] = rendered_path
    ctx.metadata["step_2_summary"] = f"Matplotlib rendered chart frames for {video_type}."
    return ctx


async def step_assemble_video(ctx: AgentContext) -> AgentContext:
    """
    Assemble the final playable asset. If ffmpeg is available, ensure an MP4.
    """

    from app.config import settings

    frames_path = ctx.metadata.get("frames_path")
    if not frames_path or not os.path.exists(frames_path):
        raise FileNotFoundError("Rendered frames asset not found")

    output_dir = settings.video_output_dir
    os.makedirs(output_dir, exist_ok=True)

    source_ext = os.path.splitext(frames_path)[1].lower() or ".mp4"
    output_path = os.path.join(output_dir, f"{ctx.run_id}.mp4")
    final_path = output_path

    if source_ext == ".mp4":
        shutil.copy2(frames_path, output_path)
    elif _can_run_ffmpeg():
        cmd = [
            "ffmpeg",
            "-y",
            "-loop",
            "1" if source_ext == ".png" else "0",
            "-i",
            frames_path,
            "-pix_fmt",
            "yuv420p",
            output_path,
        ]
        if source_ext == ".png":
            cmd[1:1] = ["-t", "4"]
        completed = await asyncio.get_running_loop().run_in_executor(
            None,
            lambda: subprocess.run(cmd, capture_output=True, text=True, check=False),
        )
        if completed.returncode != 0:
            logger.warning("ffmpeg assembly failed, falling back to original asset: %s", completed.stderr.strip())
            final_path = os.path.join(output_dir, f"{ctx.run_id}{source_ext}")
            shutil.copy2(frames_path, final_path)
        else:
            final_path = output_path
    else:
        final_path = os.path.join(output_dir, f"{ctx.run_id}{source_ext}")
        shutil.copy2(frames_path, final_path)

    ctx.video_path = final_path
    size_kb = os.path.getsize(final_path) // 1024 if os.path.exists(final_path) else 0
    ctx.metadata["step_3_summary"] = (
        f"Assembled final video asset: {os.path.basename(final_path)} ({size_kb} KB)."
    )
    return ctx


def create_video_pipeline(video_type: str = "MARKET_WRAP") -> AgentOrchestrator:
    """Return a configured Video Engine pipeline."""

    return AgentOrchestrator(
        "Video Engine",
        [
            AgentStep(
                "Market Data Ingestion",
                "Pulling live indices, sectors, FII/DII, and IPO data",
                step_ingest_market_snapshot,
            ),
            AgentStep(
                "Script Generation",
                "Claude writing a market video narration script",
                step_generate_narration,
            ),
            AgentStep(
                "Chart Rendering",
                "Matplotlib generating animated chart frames",
                step_render_charts,
            ),
            AgentStep(
                "Video Assembly",
                "Assembling the final playable video asset",
                step_assemble_video,
            ),
        ],
    )
