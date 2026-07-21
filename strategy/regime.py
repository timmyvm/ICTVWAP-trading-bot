"""
Market Regime Detector.

Determines whether the market is ranging, trending, or in a news spike,
using VWAP slope and ATR ratio as the two key inputs.

Why it matters:
  VWAP mean reversion only works in RANGING markets. In TRENDING markets,
  price can stay at -2 SD for a long time and keep going. In NEWS regimes,
  volatility is random and no strategy edge applies.

Three regimes:
  RANGING  — Flat VWAP slope + normal ATR. Mean reversion setups valid.
  TRENDING — VWAP slope is steep OR ATR is elevated. Trend-following preferred.
  NEWS     — ATR is 2x+ above average. Sit out entirely.

Regime changes are logged so you can see exactly when the bot's opinion
of the market shifts.
"""

import logging
from typing import Optional

import numpy as np
import pandas as pd

import config
from strategy.vwap import VWAPData, VWAPCalculator

logger = logging.getLogger(__name__)


class RegimeDetector:
    """
    Classifies market regime on each update.

    Usage:
        detector = RegimeDetector()
        regime = detector.get_regime(vwap_data, df_5m)
        # returns "RANGING", "TRENDING", or "NEWS"
    """

    def __init__(self):
        self._last_regime: Optional[str] = None

    def get_regime(self, vwap_data: VWAPData, df: pd.DataFrame) -> str:
        """
        Determine the current market regime.

        Args:
            vwap_data: Current VWAP data (must be fresh for accurate slope).
            df:        OHLCV DataFrame (5m recommended) for ATR computation.

        Returns:
            "RANGING" | "TRENDING" | "NEWS"
        """
        if vwap_data is None:
            # No VWAP data yet (e.g. session just started) — treat as RANGING
            return "RANGING"

        # --- ATR ratio: current ATR vs 20-period average ATR ---
        atr_ratio = self._compute_atr_ratio(df)
        slope_abs = abs(vwap_data.slope)

        # --- NEWS: extreme volatility — sit out ---
        # ATR is 2x its recent average, meaning a news spike is in progress.
        if atr_ratio >= 2.0:
            regime = "NEWS"

        # --- TRENDING: meaningful VWAP slope OR elevated ATR ---
        # Either price has a directional bias (slope) OR volatility is above normal.
        # Both conditions suggest mean-reversion is unreliable right now.
        elif slope_abs >= config.VWAP_SLOPE_THRESHOLD or atr_ratio >= 1.5:
            regime = "TRENDING"

        # --- RANGING: flat VWAP + normal ATR ---
        # Price is oscillating around VWAP with no strong direction.
        # This is the ideal environment for VWAP mean reversion.
        else:
            regime = "RANGING"

        # Log regime transitions
        if regime != self._last_regime:
            if self._last_regime is not None:
                logger.info(
                    "Regime shift: %s -> %s (slope=%.4f, atr_ratio=%.2f)",
                    self._last_regime, regime, slope_abs, atr_ratio,
                )
            else:
                logger.info(
                    "Regime initialized: %s (slope=%.4f, atr_ratio=%.2f)",
                    regime, slope_abs, atr_ratio,
                )
            self._last_regime = regime

        logger.debug(
            "Regime: %s | slope=%.4f (threshold=%.3f) | atr_ratio=%.2f",
            regime, slope_abs, config.VWAP_SLOPE_THRESHOLD, atr_ratio,
        )

        return regime

    @staticmethod
    def _compute_atr_ratio(df: pd.DataFrame) -> float:
        """
        Compute ratio of current ATR to 20-period average ATR.

        A ratio of 1.0 = normal volatility.
        A ratio of 1.5 = elevated (trending or choppy).
        A ratio of 2.0 = news/spike regime.
        """
        if len(df) < 3:
            return 1.0

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

        # Current ATR = mean of the last 3 TR values. A single candle's TR made
        # the regime flap to TRENDING/NEWS on any one wide candle, randomly
        # blocking valid mean-reversion entries; 3 candles keeps it responsive
        # without the flapping.
        current_tr = tr.iloc[-3:].mean()

        # Average ATR = 20-period rolling mean for baseline comparison
        avg_atr_len = min(config.ATR_PERIOD, len(df))
        avg_atr = tr.rolling(avg_atr_len, min_periods=2).mean().iloc[-1]

        if avg_atr <= 0 or np.isnan(avg_atr) or np.isnan(current_tr):
            return 1.0

        return float(current_tr / avg_atr)
