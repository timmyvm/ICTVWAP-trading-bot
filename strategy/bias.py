"""
HTF Bias Module — determines directional bias using 1H and 4H structure.

ICT Concept: Before looking for entries, we need to know WHICH DIRECTION to trade.
The higher-timeframe (HTF) bias tells us whether to look for longs or shorts.

Rules implemented:
1. Bullish bias: price closes above the most recent 1H/4H swing high,
   OR price is retracing into a Discount FVG (below 0.5 of the most recent leg).
2. Bearish bias: price closes below the most recent 1H/4H swing low (MSS),
   OR price is retracing into a Premium FVG (above 0.5 of the most recent leg).
3. NWOG override: an unfilled New Week Opening Gap below price forces BEARISH bias
   until that gap is tapped — the market "owes" a visit to that inefficiency.
"""

import logging
from typing import Optional

import pandas as pd

import config

logger = logging.getLogger(__name__)


def find_swing_highs(df: pd.DataFrame, lookback: int = 5) -> pd.Series:
    """
    Identify swing highs: a bar whose high is higher than `lookback` bars on each side.
    Returns a boolean Series.
    """
    highs = df["high"]
    swing = pd.Series(False, index=df.index)
    for i in range(lookback, len(df) - lookback):
        window = highs.iloc[i - lookback : i + lookback + 1]
        if highs.iloc[i] == window.max():
            swing.iloc[i] = True
    return swing


def find_swing_lows(df: pd.DataFrame, lookback: int = 5) -> pd.Series:
    """
    Identify swing lows: a bar whose low is lower than `lookback` bars on each side.
    """
    lows = df["low"]
    swing = pd.Series(False, index=df.index)
    for i in range(lookback, len(df) - lookback):
        window = lows.iloc[i - lookback : i + lookback + 1]
        if lows.iloc[i] == window.min():
            swing.iloc[i] = True
    return swing


def detect_fvg(df: pd.DataFrame) -> list[dict]:
    """
    Detect Fair Value Gaps (FVGs) in OHLCV data.

    ICT Concept: An FVG is a 3-candle pattern where:
    - Bullish FVG: candle 3's low is above candle 1's high (gap up)
    - Bearish FVG: candle 3's high is below candle 1's low (gap down)

    These gaps represent institutional order flow and price is expected to
    return to fill them.
    """
    fvgs = []
    for i in range(2, len(df)):
        c1 = df.iloc[i - 2]
        c3 = df.iloc[i]

        # Bullish FVG: gap between candle 1 high and candle 3 low
        if c3["low"] > c1["high"]:
            fvgs.append({
                "type": "bullish",
                "top": c3["low"],
                "bottom": c1["high"],
                "midpoint": (c3["low"] + c1["high"]) / 2,
                "timestamp": df.index[i],
            })

        # Bearish FVG: gap between candle 3 high and candle 1 low
        if c3["high"] < c1["low"]:
            fvgs.append({
                "type": "bearish",
                "top": c1["low"],
                "bottom": c3["high"],
                "midpoint": (c1["low"] + c3["high"]) / 2,
                "timestamp": df.index[i],
            })

    return fvgs


class HTFBias:
    """
    Determines higher-timeframe directional bias.

    Call `evaluate()` with 1H and 4H candle DataFrames + current price
    to get "BULLISH", "BEARISH", or "NEUTRAL".
    """

    def __init__(self):
        self.current_bias: Optional[str] = None
        self.nwog_level: Optional[float] = None  # Set externally by KeyLevels

    def set_nwog(self, nwog_ce: Optional[float]):
        """
        Called by KeyLevels when NWOG is calculated.
        If there is an unfilled NWOG below current price, it overrides bias to BEARISH.
        """
        self.nwog_level = nwog_ce

    def evaluate(
        self,
        df_1h: pd.DataFrame,
        df_4h: pd.DataFrame,
        current_price: float,
    ) -> str:
        """
        Determine HTF bias based on structure and FVGs.

        Returns: "BULLISH", "BEARISH", or "NEUTRAL"
        """
        if df_1h.empty or df_4h.empty:
            logger.warning("Empty candle data — returning NEUTRAL bias")
            self.current_bias = "NEUTRAL"
            return "NEUTRAL"

        # --- NWOG Override ---
        # ICT Rule: if there's an unfilled NWOG below price, the market needs
        # to reach down and tap it. Bias stays bearish until it does.
        # Proximity filter: only applies if NWOG is within NWOG_OVERRIDE_MAX_PCT
        # of current price. If NWOG is too far away, it shouldn't force bias.
        if self.nwog_level is not None and current_price > self.nwog_level:
            distance_pct = ((current_price - self.nwog_level) / current_price) * 100
            if distance_pct <= config.NWOG_OVERRIDE_MAX_PCT:
                logger.info(
                    "NWOG override: unfilled gap at %.2f (%.1f%% below price %.2f) -> BEARISH",
                    self.nwog_level,
                    distance_pct,
                    current_price,
                )
                self.current_bias = "BEARISH"
                return "BEARISH"
            else:
                logger.info(
                    "NWOG at %.2f is %.1f%% away (> %.1f%% max) — ignoring override",
                    self.nwog_level,
                    distance_pct,
                    config.NWOG_OVERRIDE_MAX_PCT,
                )

        # --- Swing Structure ---
        swing_highs_1h = find_swing_highs(df_1h)
        swing_lows_1h = find_swing_lows(df_1h)
        swing_highs_4h = find_swing_highs(df_4h)
        swing_lows_4h = find_swing_lows(df_4h)

        # Most recent swing high and low
        recent_sh_1h = df_1h.loc[swing_highs_1h, "high"].iloc[-1] if swing_highs_1h.any() else None
        recent_sl_1h = df_1h.loc[swing_lows_1h, "low"].iloc[-1] if swing_lows_1h.any() else None
        recent_sh_4h = df_4h.loc[swing_highs_4h, "high"].iloc[-1] if swing_highs_4h.any() else None
        recent_sl_4h = df_4h.loc[swing_lows_4h, "low"].iloc[-1] if swing_lows_4h.any() else None

        latest_close = df_1h["close"].iloc[-1]

        # Bullish: close above most recent swing high (Market Structure Shift to the upside)
        bullish_structure = False
        if recent_sh_1h and latest_close > recent_sh_1h:
            bullish_structure = True
        if recent_sh_4h and latest_close > recent_sh_4h:
            bullish_structure = True

        # Bearish: close below most recent swing low (Market Structure Shift to the downside)
        bearish_structure = False
        if recent_sl_1h and latest_close < recent_sl_1h:
            bearish_structure = True
        if recent_sl_4h and latest_close < recent_sl_4h:
            bearish_structure = True

        # --- FVG Retracement Check ---
        # ICT Concept: even without a clean break of structure, if price is retracing
        # into a discount FVG, bias can be bullish (buying the dip into value).
        fvgs_1h = detect_fvg(df_1h)
        fvgs_4h = detect_fvg(df_4h)
        all_fvgs = fvgs_1h + fvgs_4h

        # Check for retracement into discount FVG (bullish signal)
        if recent_sh_1h and recent_sl_1h:
            leg_midpoint = (recent_sh_1h + recent_sl_1h) / 2
            for fvg in all_fvgs:
                if fvg["type"] == "bullish" and fvg["midpoint"] < leg_midpoint:
                    # Price is in the discount zone of the leg AND there's a bullish FVG
                    if fvg["bottom"] <= current_price <= fvg["top"]:
                        bullish_structure = True
                        logger.info("Discount FVG retracement detected -> bullish")

                if fvg["type"] == "bearish" and fvg["midpoint"] > leg_midpoint:
                    # Price is in the premium zone AND there's a bearish FVG
                    if fvg["bottom"] <= current_price <= fvg["top"]:
                        bearish_structure = True
                        logger.info("Premium FVG retracement detected -> bearish")

        # --- Resolve ---
        if bullish_structure and not bearish_structure:
            self.current_bias = "BULLISH"
        elif bearish_structure and not bullish_structure:
            self.current_bias = "BEARISH"
        else:
            # Conflicting or no clear signal
            self.current_bias = "NEUTRAL"

        logger.info("HTF Bias: %s (close=%.2f)", self.current_bias, latest_close)
        return self.current_bias
