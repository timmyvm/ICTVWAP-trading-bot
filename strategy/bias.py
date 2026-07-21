"""
HTF Bias Module — determines directional bias using 1H and 4H structure.

ICT Concept: Before looking for entries, we need to know WHICH DIRECTION to trade.
The higher-timeframe (HTF) bias tells us whether to look for longs or shorts.

Rules implemented:
1. 4H structure is the primary anchor. If price closes above the most recent 4H
   swing high → BULLISH. Below the most recent 4H swing low → BEARISH. This is
   returned immediately without consulting 1H at all.
2. Only when 4H is genuinely neutral (price is between the 4H swing high and low)
   do we fall back to 1H structure breaks for a directional read.
3. 1H FVG retracements add confluence only when 4H AND 1H structure are both
   neutral. They never override or cancel a clear 4H structural read.
4. FVG checks are limited to the most recent FVG_LOOKBACK candles to prevent
   stale historical gaps from flooding both bullish and bearish signals.
5. NWOG override: an unfilled New Week Opening Gap below price forces BEARISH bias
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
        # Gated behind NWOG_BIAS_OVERRIDE: forcing BEARISH under an up-gap in a
        # bullish week shorts into strength, so the override is opt-in. The CE
        # remains a DOL target regardless.
        if (
            config.NWOG_BIAS_OVERRIDE
            and self.nwog_level is not None
            and current_price > self.nwog_level
        ):
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

        # --- Step 1: 4H Structure (primary anchor) ---
        # 4H breaks are the highest-priority signal. If 4H gives a clear directional
        # read, return immediately — 1H signals do not override it.
        #
        # Use lookback=2 (not the default 5) so that swings within the last 8 hours
        # are still detectable. The default lookback=5 would exclude the last 20 hours
        # of 4H candles from ever being swing candidates, causing the early return to
        # never fire during active market moves.
        swing_highs_4h = find_swing_highs(df_4h, lookback=2)
        swing_lows_4h = find_swing_lows(df_4h, lookback=2)

        recent_sh_4h = df_4h.loc[swing_highs_4h, "high"].iloc[-1] if swing_highs_4h.any() else None
        recent_sl_4h = df_4h.loc[swing_lows_4h, "low"].iloc[-1] if swing_lows_4h.any() else None

        latest_close = df_1h["close"].iloc[-1]

        htf_bullish = recent_sh_4h is not None and latest_close > recent_sh_4h
        htf_bearish = recent_sl_4h is not None and latest_close < recent_sl_4h

        if htf_bullish and not htf_bearish:
            self.current_bias = "BULLISH"
            logger.info(
                "HTF Bias: BULLISH (4H MSS — close %.2f > 4H swing high %.2f)",
                latest_close, recent_sh_4h,
            )
            return "BULLISH"

        if htf_bearish and not htf_bullish:
            self.current_bias = "BEARISH"
            logger.info(
                "HTF Bias: BEARISH (4H MSS — close %.2f < 4H swing low %.2f)",
                latest_close, recent_sl_4h,
            )
            return "BEARISH"

        # --- Step 2: 4H is neutral — check 1H structure for confluence ---
        # Price is between the 4H swing high and low (no 4H structure break yet).
        # Use 1H swing breaks as a secondary read.
        swing_highs_1h = find_swing_highs(df_1h)
        swing_lows_1h = find_swing_lows(df_1h)

        recent_sh_1h = df_1h.loc[swing_highs_1h, "high"].iloc[-1] if swing_highs_1h.any() else None
        recent_sl_1h = df_1h.loc[swing_lows_1h, "low"].iloc[-1] if swing_lows_1h.any() else None

        bullish_structure = recent_sh_1h is not None and latest_close > recent_sh_1h
        bearish_structure = recent_sl_1h is not None and latest_close < recent_sl_1h

        # --- Step 3: FVG Confluence (1H only, recent candles only) ---
        # FVGs are checked only when both 4H and 1H structure are ambiguous.
        # Limit to the last FVG_LOOKBACK candles to avoid stale historical gaps
        # flooding both bullish and bearish signals simultaneously across a wide range.
        FVG_LOOKBACK = 20
        recent_fvgs_1h = detect_fvg(df_1h.iloc[-FVG_LOOKBACK:])

        if recent_sh_1h and recent_sl_1h:
            leg_midpoint = (recent_sh_1h + recent_sl_1h) / 2
            for fvg in recent_fvgs_1h:
                if fvg["type"] == "bullish" and fvg["midpoint"] < leg_midpoint:
                    if fvg["bottom"] <= current_price <= fvg["top"]:
                        bullish_structure = True
                        logger.info("1H Discount FVG retracement -> bullish confluence")

                if fvg["type"] == "bearish" and fvg["midpoint"] > leg_midpoint:
                    if fvg["bottom"] <= current_price <= fvg["top"]:
                        bearish_structure = True
                        logger.info("1H Premium FVG retracement -> bearish confluence")

        # --- Resolve ---
        if bullish_structure and not bearish_structure:
            self.current_bias = "BULLISH"
        elif bearish_structure and not bullish_structure:
            self.current_bias = "BEARISH"
        else:
            # Conflicting 1H signals or no structure break on any timeframe
            self.current_bias = "NEUTRAL"

        logger.info("HTF Bias: %s (close=%.2f)", self.current_bias, latest_close)
        return self.current_bias
