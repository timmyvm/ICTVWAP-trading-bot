"""
VWAP (Volume Weighted Average Price) Calculator.

Calculates session VWAP resetting at 00:00 NY Time daily, with standard
deviation bands and slope for the VWAP Mean Reversion strategy.

Concept: VWAP acts as institutional "fair value". When price deviates
significantly from VWAP (2-3 standard deviations), it tends to mean-revert
— especially in ranging markets where directional momentum is absent.

Key outputs:
  vwap        — session VWAP (cumulative, resets at midnight NY)
  upper_1/2/3 — VWAP + 1x/2x/3x rolling standard deviation
  lower_1/2/3 — VWAP - 1x/2x/3x rolling standard deviation
  slope       — VWAP slope over last 10 candles (linear regression, normalised by ATR)
  vol_avg     — 20-period volume moving average (used for volume filter)
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd
import pytz

import config

logger = logging.getLogger(__name__)

NY_TZ = pytz.timezone("America/New_York")


@dataclass
class VWAPData:
    """Current VWAP values and all derived band levels."""

    vwap: float
    upper_1: float
    upper_2: float
    upper_3: float
    lower_1: float
    lower_2: float
    lower_3: float
    slope: float        # Normalised VWAP slope (slope_pts_per_candle / ATR)
    vol_avg: float      # 20-period volume moving average
    std: float          # Current standard deviation (raw, for diagnostics)
    session_candles: int  # How many candles are in today's session


class VWAPCalculator:
    """
    Computes session VWAP and standard deviation bands.

    Session resets at VWAP_SESSION_RESET_HOUR (default 00:00) NY Time each day.
    Uses typical price = (high + low + close) / 3 as the price anchor.
    Standard deviation is a rolling window over VWAP_STD_LENGTH (20) periods
    of the deviation (close - vwap), giving adaptive bands.
    """

    def compute(self, df: pd.DataFrame) -> Optional[VWAPData]:
        """
        Compute VWAP and bands from OHLCV DataFrame.

        Args:
            df: OHLCV DataFrame indexed by NY-time datetime. Must have at least
                VWAP_STD_LENGTH candles in the current session to produce valid bands.

        Returns:
            VWAPData if enough session data is available, else None.
        """
        if df.empty or len(df) < 5:
            return None

        # --- Step 1: Isolate today's session (since midnight NY) ---
        now_ny = datetime.now(NY_TZ)
        session_start = now_ny.replace(
            hour=config.VWAP_SESSION_RESET_HOUR,
            minute=0,
            second=0,
            microsecond=0,
        )

        # Ensure index is tz-aware for comparison
        idx = df.index
        if idx.tzinfo is None:
            idx = idx.tz_localize(NY_TZ)
        elif str(idx.tzinfo) != str(NY_TZ):
            idx = idx.tz_convert(NY_TZ)

        session_mask = idx >= session_start
        session_df = df[session_mask].copy()

        if len(session_df) < 3:
            logger.debug(
                "VWAP: only %d session candles available (need ≥3)", len(session_df)
            )
            return None

        # --- Step 2: Cumulative VWAP ---
        # Typical price = (H + L + C) / 3 — standard VWAP anchor
        session_df["tp"] = (
            session_df["high"] + session_df["low"] + session_df["close"]
        ) / 3

        session_df["tp_vol"] = session_df["tp"] * session_df["volume"]
        session_df["cum_tp_vol"] = session_df["tp_vol"].cumsum()
        session_df["cum_vol"] = session_df["volume"].cumsum()

        # Guard against zero volume sessions (e.g. testnet dry spells)
        if session_df["cum_vol"].iloc[-1] == 0:
            logger.warning("VWAP: zero cumulative volume in session — skipping")
            return None

        session_df["vwap"] = session_df["cum_tp_vol"] / session_df["cum_vol"]

        current_vwap = session_df["vwap"].iloc[-1]

        # --- Step 3: Rolling standard deviation of deviation from VWAP ---
        # Deviation = how far close is from VWAP each candle
        session_df["deviation"] = session_df["close"] - session_df["vwap"]

        std_len = min(config.VWAP_STD_LENGTH, len(session_df))
        std_series = session_df["deviation"].rolling(std_len, min_periods=2).std()
        current_std = std_series.iloc[-1]

        if current_std is None or np.isnan(current_std) or current_std <= 0:
            logger.debug("VWAP: std not yet valid (only %d candles)", len(session_df))
            return None

        # --- Step 4: Bands ---
        upper_1 = current_vwap + 1.0 * current_std
        upper_2 = current_vwap + 2.0 * current_std
        upper_3 = current_vwap + 3.0 * current_std
        lower_1 = current_vwap - 1.0 * current_std
        lower_2 = current_vwap - 2.0 * current_std
        lower_3 = current_vwap - 3.0 * current_std

        # --- Step 5: VWAP slope (linear regression over last 10 candles, normalised by ATR) ---
        slope = self._compute_slope(session_df, df)

        # --- Step 6: Volume moving average (20-period, uses full df not just session) ---
        vol_avg_len = min(config.VWAP_STD_LENGTH, len(df))
        vol_avg = df["volume"].rolling(vol_avg_len).mean().iloc[-1]
        if np.isnan(vol_avg):
            vol_avg = df["volume"].mean()

        logger.debug(
            "VWAP: %.2f | +1σ=%.2f +2σ=%.2f +3σ=%.2f | "
            "-1σ=%.2f -2σ=%.2f -3σ=%.2f | slope=%.4f std=%.2f bars=%d",
            current_vwap,
            upper_1, upper_2, upper_3,
            lower_1, lower_2, lower_3,
            slope, current_std, len(session_df),
        )

        return VWAPData(
            vwap=current_vwap,
            upper_1=upper_1,
            upper_2=upper_2,
            upper_3=upper_3,
            lower_1=lower_1,
            lower_2=lower_2,
            lower_3=lower_3,
            slope=slope,
            vol_avg=float(vol_avg),
            std=current_std,
            session_candles=len(session_df),
        )

    @staticmethod
    def _compute_slope(session_df: pd.DataFrame, full_df: pd.DataFrame) -> float:
        """
        Compute VWAP slope via linear regression over the last 10 session candles,
        normalised by the current 14-period ATR so slope is dimensionless.

        A slope of 0.01 means VWAP is drifting 1% of ATR per candle — significant.
        Near-zero slope confirms a ranging, mean-reverting environment.
        """
        vwap_window = session_df["vwap"].iloc[-10:].dropna()
        if len(vwap_window) < 3:
            return 0.0

        x = np.arange(len(vwap_window))
        try:
            coeffs = np.polyfit(x, vwap_window.values, 1)
            slope_pts_per_candle = coeffs[0]  # In price points per candle
        except (np.linalg.LinAlgError, ValueError):
            return 0.0

        # Normalise by ATR so slope is comparable across different price regimes
        atr = VWAPCalculator._compute_atr(full_df)
        if atr > 0:
            return float(slope_pts_per_candle / atr)

        return 0.0

    @staticmethod
    def _compute_atr(df: pd.DataFrame, period: int = 14) -> float:
        """Compute Average True Range over `period` candles."""
        if len(df) < 2:
            return 1.0  # Fallback — avoid division by zero

        high = df["high"]
        low = df["low"]
        prev_close = df["close"].shift(1)

        tr = pd.concat(
            [
                high - low,
                (high - prev_close).abs(),
                (low - prev_close).abs(),
            ],
            axis=1,
        ).max(axis=1)

        atr_series = tr.rolling(period, min_periods=1).mean()
        val = atr_series.iloc[-1]
        return float(val) if not np.isnan(val) else 1.0
