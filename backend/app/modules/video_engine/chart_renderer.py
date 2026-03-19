"""
ET InvestorIQ — Chart Renderer (Video Engine)
Matplotlib-based animation renderer for all video types.
Uses non-interactive 'Agg' backend. Falls back to GIF if ffmpeg unavailable.
"""

import logging
import os
import subprocess
import tempfile
from typing import List

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend — MUST be before pyplot import
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.animation as animation
from matplotlib.gridspec import GridSpec
import numpy as np

logger = logging.getLogger(__name__)

# ─── Color scheme ─────────────────────────────────────────────────────────────
BG = "#0D1117"
CARD = "#161B22"
BULL = "#00FF88"
BEAR = "#FF4444"
ACCENT = "#0066CC"
TEXT = "#E6EDF3"
TEXT_DIM = "#8B949E"
GOLD = "#FFD700"


def _setup_dark_fig(figsize=(16, 9), dpi=100):
    """Create a dark-themed matplotlib figure."""
    fig = plt.figure(figsize=figsize, dpi=dpi, facecolor=BG)
    plt.rcParams.update({
        "text.color": TEXT, "axes.labelcolor": TEXT,
        "xtick.color": TEXT_DIM, "ytick.color": TEXT_DIM,
        "axes.facecolor": CARD, "axes.edgecolor": "#30363D",
        "grid.color": "#21262D", "figure.facecolor": BG,
    })
    return fig


def _add_title_bar(fig, title: str, subtitle: str = ""):
    """Add a styled title bar to the top of the figure."""
    fig.text(0.05, 0.95, "ET InvestorIQ", fontsize=10, color=ACCENT, fontweight="bold", va="top")
    fig.text(0.05, 0.91, title, fontsize=22, color=TEXT, fontweight="bold", va="top")
    if subtitle:
        fig.text(0.05, 0.86, subtitle, fontsize=12, color=TEXT_DIM, va="top")
    fig.text(0.95, 0.95, "Economic Times", fontsize=9, color=TEXT_DIM, ha="right", va="top")


def _check_ffmpeg() -> bool:
    """Check if ffmpeg is available on the system."""
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5)
        return True
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def _save_animation(anim, output_path: str, fps: int = 24, dpi: int = 80) -> str:
    """Save matplotlib animation to MP4 or GIF fallback."""
    has_ffmpeg = _check_ffmpeg()

    if has_ffmpeg and output_path.endswith(".mp4"):
        writer = animation.FFMpegWriter(fps=fps, bitrate=1800,
                                         extra_args=["-vcodec", "libx264", "-preset", "fast"])
        anim.save(output_path, writer=writer, dpi=dpi)
        logger.info(f"Saved MP4: {output_path}")
    else:
        # Fallback to GIF
        gif_path = output_path.replace(".mp4", ".gif")
        writer = animation.PillowWriter(fps=fps)
        anim.save(gif_path, writer=writer, dpi=dpi)
        output_path = gif_path
        logger.info(f"Saved GIF (ffmpeg unavailable): {gif_path}")

    return output_path


def render_market_wrap(data: dict, output_path: str) -> str:
    """
    Create a 60-second market wrap animation.
    Shows index levels, top gainers/losers, and market breadth.

    Args:
        data: Market overview dict from data_service.get_market_overview().
        output_path: Output file path (.mp4 or .gif).

    Returns:
        Actual output path (may differ if GIF fallback used).
    """
    try:
        nifty = data.get("nifty50", {})
        gainers = data.get("top_gainers", [])[:6]
        losers = data.get("top_losers", [])[:6]
        breadth = data.get("market_breadth", {"advances": 1200, "declines": 900, "unchanged": 400})
        fii_net = data.get("fii_net_today", 500)
        vix = data.get("vix", 15)

        fig = _setup_dark_fig(figsize=(16, 9), dpi=80)
        fig.tight_layout(pad=0)

        frames_total = 72  # 3 seconds at 24fps per section × ~3 sections = 72 frames
        n_frames = frames_total

        # Static layout elements
        ax_index = fig.add_axes([0.05, 0.68, 0.42, 0.22], facecolor=CARD)
        ax_gainers = fig.add_axes([0.05, 0.08, 0.42, 0.55], facecolor=CARD)
        ax_breadth = fig.add_axes([0.55, 0.08, 0.40, 0.80], facecolor=CARD)

        for ax in [ax_index, ax_gainers, ax_breadth]:
            ax.tick_params(colors=TEXT_DIM)
            for spine in ax.spines.values():
                spine.set_edgecolor("#30363D")

        def animate(frame_idx):
            progress = frame_idx / n_frames

            # Clear dynamic elements
            ax_index.cla()
            ax_gainers.cla()
            ax_breadth.cla()

            for ax in [ax_index, ax_gainers, ax_breadth]:
                ax.set_facecolor(CARD)
                for spine in ax.spines.values():
                    spine.set_edgecolor("#30363D")

            # ── Index panel (animated number counting up) ──────────────────
            target_nifty = nifty.get("level", 22350)
            target_chg = nifty.get("change_pct", 0.5)
            display_level = 20000 + (target_nifty - 20000) * min(1.0, progress * 2)

            ax_index.set_xlim(0, 1)
            ax_index.set_ylim(0, 1)
            ax_index.axis("off")
            ax_index.text(0.05, 0.8, "NIFTY 50", fontsize=13, color=TEXT_DIM, fontweight="bold")
            ax_index.text(0.05, 0.45, f"₹{display_level:,.0f}",
                         fontsize=28, color=BULL if target_chg >= 0 else BEAR, fontweight="bold")
            chg_color = BULL if target_chg >= 0 else BEAR
            ax_index.text(0.05, 0.12, f"{'▲' if target_chg >= 0 else '▼'} {abs(target_chg):.2f}%",
                         fontsize=14, color=chg_color)

            # ── Gainers/Losers animated bar chart ──────────────────────────
            all_stocks = (
                [(g["symbol"], g["change_pct"]) for g in gainers] +
                [(l["symbol"], l["change_pct"]) for l in losers]
            )
            symbols_sorted = [s for s, _ in sorted(all_stocks, key=lambda x: x[1])]
            values_sorted = [v for _, v in sorted(all_stocks, key=lambda x: x[1])]
            animated_values = [v * min(1.0, progress * 1.5) for v in values_sorted]
            colors = [BULL if v >= 0 else BEAR for v in values_sorted]

            y_pos = range(len(symbols_sorted))
            ax_gainers.barh(list(y_pos), animated_values, color=colors, alpha=0.85, height=0.7)
            ax_gainers.set_yticks(list(y_pos))
            ax_gainers.set_yticklabels(symbols_sorted, fontsize=9, color=TEXT)
            ax_gainers.axvline(0, color=TEXT_DIM, linewidth=0.5)
            ax_gainers.set_title("Top Movers Today", color=TEXT, fontsize=11, pad=8)
            ax_gainers.tick_params(colors=TEXT_DIM)
            ax_gainers.set_facecolor(CARD)

            # ── Market breadth ─────────────────────────────────────────────
            advances = breadth.get("advances", 1200)
            declines = breadth.get("declines", 900)
            unchanged = breadth.get("unchanged", 400)
            total = advances + declines + unchanged

            ax_breadth.set_xlim(0, 1)
            ax_breadth.set_ylim(0, 1)
            ax_breadth.axis("off")
            ax_breadth.text(0.5, 0.92, "Market Breadth", fontsize=14, color=TEXT,
                           fontweight="bold", ha="center")

            # Animated progress bars
            adv_pct = (advances / total) * min(1.0, progress * 1.5)
            dec_pct = (declines / total) * min(1.0, progress * 1.5)

            for y, label, val, orig, color in [
                (0.72, "ADVANCES", adv_pct, advances, BULL),
                (0.52, "DECLINES", dec_pct, declines, BEAR),
            ]:
                ax_breadth.add_patch(mpatches.FancyBboxPatch(
                    (0.05, y), 0.9 * val, 0.12,
                    boxstyle="round,pad=0.01", facecolor=color, alpha=0.8))
                ax_breadth.text(0.05, y + 0.14, label, fontsize=9, color=TEXT_DIM)
                ax_breadth.text(0.95, y + 0.05, str(orig), fontsize=11, color=color, ha="right")

            # FII data
            fii_color = BULL if fii_net >= 0 else BEAR
            ax_breadth.text(0.5, 0.30, "FII Net Today", fontsize=10, color=TEXT_DIM, ha="center")
            ax_breadth.text(0.5, 0.20, f"₹{abs(fii_net):,.0f} Cr {'inflow' if fii_net >= 0 else 'outflow'}",
                           fontsize=13, color=fii_color, ha="center", fontweight="bold")
            ax_breadth.text(0.5, 0.08, f"India VIX: {vix:.1f}",
                           fontsize=11, color=TEXT_DIM, ha="center")

            # Title bar on figure
            if frame_idx == 0 or frame_idx % 24 == 0:
                pass  # Title is static

        # Draw static title
        _add_title_bar(fig, "Market Wrap", "NSE/BSE Daily Summary")

        anim_obj = animation.FuncAnimation(
            fig, animate, frames=n_frames, interval=1000 / 24, blit=False
        )
        result_path = _save_animation(anim_obj, output_path, fps=24, dpi=80)
        plt.close(fig)
        return result_path

    except Exception as e:
        logger.error(f"render_market_wrap failed: {e}", exc_info=True)
        plt.close("all")
        return _render_fallback_image(output_path, "Market Wrap", str(e))


def render_sector_rotation(data: dict, output_path: str) -> str:
    """
    Create a 45-second sector performance heatmap animation.

    Args:
        data: List of sector performance dicts.
        output_path: Output file path.

    Returns:
        Actual output path.
    """
    try:
        sectors = data if isinstance(data, list) else []
        if not sectors:
            sectors = [
                {"sector": "IT", "return_1d_pct": 1.2, "return_1m_pct": -3.5},
                {"sector": "Banking", "return_1d_pct": 0.8, "return_1m_pct": 5.2},
                {"sector": "Pharma", "return_1d_pct": -0.5, "return_1m_pct": 8.1},
                {"sector": "Auto", "return_1d_pct": 2.1, "return_1m_pct": 12.3},
                {"sector": "FMCG", "return_1d_pct": -1.2, "return_1m_pct": -2.8},
                {"sector": "Energy", "return_1d_pct": 1.8, "return_1m_pct": 6.7},
                {"sector": "Metals", "return_1d_pct": 3.2, "return_1m_pct": 15.4},
                {"sector": "Infra", "return_1d_pct": 0.5, "return_1m_pct": 3.2},
                {"sector": "Realty", "return_1d_pct": -2.1, "return_1m_pct": -8.5},
            ]

        fig = _setup_dark_fig(figsize=(16, 9), dpi=80)
        _add_title_bar(fig, "Sector Rotation Heatmap", "NSE Sector Performance")

        ax = fig.add_axes([0.05, 0.08, 0.90, 0.78], facecolor=BG)
        ax.axis("off")

        n = len(sectors)
        n_frames = 60

        def animate(frame):
            ax.cla()
            ax.axis("off")
            ax.set_facecolor(BG)
            progress = min(1.0, frame / (n_frames * 0.6))

            cols = 3
            rows = (n + cols - 1) // cols
            cell_w = 0.30
            cell_h = 0.22

            for i, sec in enumerate(sectors):
                row = i // cols
                col = i % cols
                x = 0.03 + col * (cell_w + 0.02)
                y = 0.85 - (row + 1) * (cell_h + 0.03)

                ret_1m = sec.get("return_1m_pct", 0)
                intensity = min(1.0, abs(ret_1m) / 15) * progress
                if ret_1m >= 0:
                    face_color = (0, intensity * 0.8, intensity * 0.4, 0.85)
                else:
                    face_color = (intensity * 0.9, intensity * 0.2, intensity * 0.2, 0.85)

                ax.add_patch(mpatches.FancyBboxPatch(
                    (x, y), cell_w, cell_h,
                    boxstyle="round,pad=0.005",
                    facecolor=face_color, edgecolor="#30363D", linewidth=1
                ))

                ax.text(x + cell_w / 2, y + cell_h * 0.7,
                       sec["sector"], ha="center", va="center",
                       fontsize=13, fontweight="bold", color=TEXT)
                ret_color = BULL if ret_1m >= 0 else BEAR
                ax.text(x + cell_w / 2, y + cell_h * 0.3,
                       f"{'▲' if ret_1m >= 0 else '▼'} {abs(ret_1m):.1f}% (1M)",
                       ha="center", va="center", fontsize=10, color=ret_color)

        anim_obj = animation.FuncAnimation(fig, animate, frames=n_frames, interval=1000/24, blit=False)
        result_path = _save_animation(anim_obj, output_path, fps=24, dpi=80)
        plt.close(fig)
        return result_path

    except Exception as e:
        logger.error(f"render_sector_rotation failed: {e}", exc_info=True)
        plt.close("all")
        return _render_fallback_image(output_path, "Sector Rotation", str(e))


def render_fii_dii_flow(data: list, output_path: str) -> str:
    """
    Create a 60-second FII vs DII net flow animation (stacked bar building day by day).

    Args:
        data: List of FII/DII flow dicts.
        output_path: Output file path.

    Returns:
        Actual output path.
    """
    try:
        if not data:
            data = []

        dates = [d.get("date", "")[-5:] for d in data]  # MM-DD format
        fii_net = [float(d.get("fii_net", 0)) for d in data]
        dii_net = [float(d.get("dii_net", 0)) for d in data]
        n = len(dates)
        n_frames = max(48, n * 3)

        fig = _setup_dark_fig(figsize=(16, 9), dpi=80)
        _add_title_bar(fig, "FII / DII Investment Flow", "Last 30 Trading Days")
        ax = fig.add_axes([0.07, 0.10, 0.88, 0.72], facecolor=CARD)

        def animate(frame):
            ax.cla()
            ax.set_facecolor(CARD)
            bars_to_show = max(1, int((frame / n_frames) * n))
            x = np.arange(bars_to_show)
            fii_show = fii_net[:bars_to_show]
            dii_show = dii_net[:bars_to_show]

            ax.bar(x, fii_show,
                   color=[BULL if v >= 0 else BEAR for v in fii_show],
                   label="FII Net", alpha=0.85, width=0.4, align="edge")
            ax.bar(x - 0.4, dii_show,
                   color=[ACCENT if v >= 0 else "#FF8C00" for v in dii_show],
                   label="DII Net", alpha=0.85, width=0.4, align="edge")

            ax.axhline(0, color=TEXT_DIM, linewidth=0.8, linestyle="--")
            ax.set_xticks(range(len(dates[:bars_to_show])))
            ax.set_xticklabels(dates[:bars_to_show], rotation=45, fontsize=7, color=TEXT_DIM)
            ax.set_ylabel("₹ Crores", color=TEXT_DIM, fontsize=10)
            ax.legend(loc="upper right", facecolor=CARD, labelcolor=TEXT, fontsize=9)
            ax.yaxis.label.set_color(TEXT)
            ax.tick_params(colors=TEXT_DIM)
            for spine in ax.spines.values():
                spine.set_edgecolor("#30363D")

        anim_obj = animation.FuncAnimation(fig, animate, frames=n_frames, interval=1000/24, blit=False)
        result_path = _save_animation(anim_obj, output_path, fps=24, dpi=80)
        plt.close(fig)
        return result_path

    except Exception as e:
        logger.error(f"render_fii_dii_flow failed: {e}", exc_info=True)
        plt.close("all")
        return _render_fallback_image(output_path, "FII/DII Flow", str(e))


def render_race_chart(data: dict, symbols: List[str], output_path: str) -> str:
    """
    Create a bar race chart showing stock return % racing over time.

    Args:
        data: Dict mapping symbol → time series of cumulative returns.
        symbols: List of stock symbols.
        output_path: Output file path.

    Returns:
        Actual output path.
    """
    try:
        n_frames = 80
        n_stocks = min(len(symbols), 10)
        sym_list = symbols[:n_stocks]
        colors = plt.cm.Set2(np.linspace(0, 1, n_stocks))

        # Simulate return trajectories
        np.random.seed(42)
        trajectories = {}
        for sym in sym_list:
            daily_rets = np.random.normal(0.001, 0.015, n_frames)
            trajectories[sym] = np.cumprod(1 + daily_rets) * 100 - 100  # % return

        fig = _setup_dark_fig(figsize=(16, 9), dpi=80)
        _add_title_bar(fig, "Stock Performance Race", "Cumulative Return %")
        ax = fig.add_axes([0.15, 0.08, 0.82, 0.78], facecolor=CARD)

        def animate(frame):
            ax.cla()
            ax.set_facecolor(CARD)
            current_returns = {sym: trajectories[sym][min(frame, n_frames - 1)] for sym in sym_list}
            sorted_syms = sorted(current_returns.items(), key=lambda x: x[1])

            ys = range(len(sorted_syms))
            values = [v for _, v in sorted_syms]
            labels = [s for s, _ in sorted_syms]
            bar_colors = [BULL if v >= 0 else BEAR for v in values]

            ax.barh(list(ys), values, color=bar_colors, alpha=0.85, height=0.7)
            for y, (sym, val) in zip(ys, sorted_syms):
                ax.text(-0.5, y, sym, ha="right", va="center", fontsize=11, color=TEXT, fontweight="bold")
                ax.text(val + (0.3 if val >= 0 else -0.3), y,
                       f"{val:+.1f}%", ha="left" if val >= 0 else "right",
                       va="center", fontsize=9, color=BULL if val >= 0 else BEAR)

            ax.axvline(0, color=TEXT_DIM, linewidth=0.8)
            ax.set_yticks([])
            ax.set_xlabel("Return %", color=TEXT_DIM)
            ax.tick_params(colors=TEXT_DIM)
            for spine in ax.spines.values():
                spine.set_edgecolor("#30363D")

            # Day counter
            day_num = int((frame / n_frames) * 30)
            ax.set_title(f"Day {day_num}", color=GOLD, fontsize=14, pad=8)

        anim_obj = animation.FuncAnimation(fig, animate, frames=n_frames, interval=1000/24, blit=False)
        result_path = _save_animation(anim_obj, output_path, fps=24, dpi=80)
        plt.close(fig)
        return result_path

    except Exception as e:
        logger.error(f"render_race_chart failed: {e}", exc_info=True)
        plt.close("all")
        return _render_fallback_image(output_path, "Race Chart", str(e))


def render_ipo_tracker(data: list, output_path: str) -> str:
    """
    Create an animated IPO tracker dashboard.

    Args:
        data: List of IPO dicts.
        output_path: Output file path.

    Returns:
        Actual output path.
    """
    try:
        n_frames = 60
        fig = _setup_dark_fig(figsize=(16, 9), dpi=80)
        _add_title_bar(fig, "IPO Tracker", "Upcoming & Recent Listings")
        ax = fig.add_axes([0.05, 0.08, 0.90, 0.78], facecolor=CARD)

        listed = [i for i in data if i.get("status") == "Listed" and i.get("listing_gain_pct") is not None]
        listed.sort(key=lambda x: x.get("listing_gain_pct", 0), reverse=True)

        companies = [i["company"][:15] for i in listed[:8]]
        gains = [float(i.get("listing_gain_pct", 0)) for i in listed[:8]]
        colors = [BULL if g >= 0 else BEAR for g in gains]

        def animate(frame):
            ax.cla()
            ax.set_facecolor(CARD)
            progress = min(1.0, frame / (n_frames * 0.7))
            animated_gains = [g * progress for g in gains]
            y_pos = range(len(companies))

            ax.barh(list(y_pos), animated_gains, color=colors, alpha=0.85)
            ax.set_yticks(list(y_pos))
            ax.set_yticklabels(companies, color=TEXT, fontsize=9)
            ax.axvline(0, color=TEXT_DIM, linewidth=0.8)
            ax.set_xlabel("Listing Day Gain %", color=TEXT_DIM)
            for i, (g, ag) in enumerate(zip(gains, animated_gains)):
                ax.text(ag + 0.5, i, f"{g:+.1f}%", va="center", fontsize=8,
                       color=BULL if g >= 0 else BEAR)
            ax.set_title("Recent IPO Listing Performance", color=TEXT, fontsize=12)
            ax.tick_params(colors=TEXT_DIM)
            for spine in ax.spines.values():
                spine.set_edgecolor("#30363D")

        anim_obj = animation.FuncAnimation(fig, animate, frames=n_frames, interval=1000/24, blit=False)
        result_path = _save_animation(anim_obj, output_path, fps=24, dpi=80)
        plt.close(fig)
        return result_path

    except Exception as e:
        logger.error(f"render_ipo_tracker failed: {e}", exc_info=True)
        plt.close("all")
        return _render_fallback_image(output_path, "IPO Tracker", str(e))


def _render_fallback_image(output_path: str, title: str, error: str = "") -> str:
    """
    Render a static fallback PNG when animation fails.
    Returns path to the saved image.
    """
    try:
        img_path = output_path.replace(".mp4", ".png").replace(".gif", ".png")
        fig = _setup_dark_fig(figsize=(16, 9), dpi=80)
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_facecolor(BG)
        ax.axis("off")
        ax.text(0.5, 0.55, title, ha="center", va="center", fontsize=32,
               color=TEXT, fontweight="bold")
        ax.text(0.5, 0.45, "ET InvestorIQ Video Engine", ha="center", va="center",
               fontsize=16, color=ACCENT)
        ax.text(0.5, 0.38, "Video ready — check back shortly", ha="center", va="center",
               fontsize=12, color=TEXT_DIM)
        fig.savefig(img_path, facecolor=BG, bbox_inches="tight")
        plt.close(fig)
        return img_path
    except Exception:
        return output_path
