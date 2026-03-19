"""
ET InvestorIQ — Application Configuration
Loads all environment variables using Pydantic BaseSettings.
"""

from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Anthropic API
    anthropic_api_key: str = "your_key_here"

    # App modes
    mock_mode: bool = False

    # Redis
    redis_url: str = "redis://localhost:6379"

    # Video output directory
    video_output_dir: str = "./generated_videos"

    # CORS origins (comma-separated string parsed into list)
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse comma-separated CORS origins into a list."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    # NSE Top 50 stocks in Yahoo Finance format
    nse_top_50: List[str] = [
        "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
        "KOTAKBANK.NS", "LT.NS", "AXISBANK.NS", "BHARTIARTL.NS", "ITC.NS",
        "SBIN.NS", "HINDUNILVR.NS", "BAJFINANCE.NS", "WIPRO.NS", "ULTRACEMCO.NS",
        "TITAN.NS", "NESTLEIND.NS", "MARUTI.NS", "SUNPHARMA.NS", "TATAMOTORS.NS",
        "POWERGRID.NS", "ONGC.NS", "NTPC.NS", "ASIANPAINT.NS", "M&M.NS",
        "TECHM.NS", "ADANIENT.NS", "JSWSTEEL.NS", "TATASTEEL.NS", "HINDALCO.NS",
        "COALINDIA.NS", "DIVISLAB.NS", "DRREDDY.NS", "CIPLA.NS", "EICHERMOT.NS",
        "BAJAJ-AUTO.NS", "HEROMOTOCO.NS", "BPCL.NS", "IOC.NS", "INDUSINDBK.NS",
        "GRASIM.NS", "BRITANNIA.NS", "DABUR.NS", "PIDILITIND.NS", "HAVELLS.NS",
        "BANDHANBNK.NS", "MUTHOOTFIN.NS", "CHOLAFIN.NS", "HCLTECH.NS",
        "^NSEI",  # Nifty 50 Index
    ]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Singleton settings instance
settings = Settings()

# Ensure video output directory exists
os.makedirs(settings.video_output_dir, exist_ok=True)
