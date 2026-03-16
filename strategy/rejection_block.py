"""
Rejection Block Detection Module — the core entry trigger.

ICT / Powell Trades Concept:
A Rejection Block (RB) is NOT just any candle pattern. It has strict requirements:

1. The initial candle must form WITHIN the Fibonacci discount zone (>= 0.5 retracement)
2. There must be a liquidity sweep before or during formation:
   - For SHORTS: wick above a recent swing high (swept buy-side liquidity)
   - For LONGS: wick below a recent swing low (swept sell-side liquidity)
3. The FOLLOWING candle must confirm:
   - For SHORTS: next candle closes bearish
   - For LONGS: next candle closes bullish
4. Entry is at the opening price of the initial RB candle (the one that rejected)
5. For large blocks (range > 40 pts): use CE (50%) or 25% level instead

WHY: The RB represents institutional rejection of a price level after sweeping
liquidity. Smart money grabbed stop losses (the sweep), then aggressively
reversed — the RB candle captures that reversal intent.
"""

import logging
from dataclasses import dataclass
from typing import Optional

import pandas as pd

import config
from strategy.fibonacci import FibLevels

logger = logging.getLogger(__name__)


@dataclass
class RejectionBlock:
    """Represents a confirmed rejection block."""

    timestamp: object  # When the RB formed
    direction: str  # "LONG" or "SHORT"
    entry_price: float  # Calculated entry (open of initial candle, CE, or 25%)
    block_high: float  # High of the RB candle
    block_low: float  # Low of the RB candle
    block_range: float  # Range of the block
    manipulation_high: float  # The swept high (for shorts) or swept low (for longs)
    fib_zone: str  # Which fib zone it formed in ("equilibrium", "ote", "deep_discount")
    is_large: bool  # Whether block range > LARGE_RB_THRESHOLD
    tier: int = 1  # Two-Tier Entry Model (Powell V3):
    # Tier 1 = Premium entry: caught initial RB at optimal fib (target R:R 1:5-1:8)
    # Tier 2 = Confirmation entry: missed premium, entered later RB (target R:R 1:3)


class RejectionBlockDetector:
    """
    Scans candles on the entry timeframe for valid rejection blocks.

    Must be provided with:
    - Candle data (1m or 5m based on ENTRY_MODE)
    - Current Fibonacci levels (to validate discount zone)
    - Current bias (to know which direction to look)
    """

    def __init__(self):
        self.last_detected: Optional[RejectionBlock] = None

    def scan(
        self,
        df: pd.DataFrame,
        fib_levels: FibLevels,
        bias: str,
        swing_lookback: int = 10,
    ) -> Optional[RejectionBlock]:
        """
        Scan the most recent candles for a confirmed rejection block.

        Args:
            df: Entry-timeframe OHLCV data (1m or 5m).
            fib_levels: Current Fibonacci levels from the 1H leg.
            bias: "BULLISH" or "BEARISH".
            swing_lookback: How many candles back to look for swing points to sweep.

        Returns:
            RejectionBlock if a valid one is confirmed, else None.
        """
        if df.empty or len(df) < swing_lookback + 2:
            return None

        # We check the second-to-last candle as the "initial" and the last as "confirmation"
        # because the last candle just closed — that's the confirmation candle.
        initial = df.iloc[-2]
        confirmation = df.iloc[-1]

        if bias == "BULLISH":
            return self._check_bullish_rb(df, initial, confirmation, fib_levels, swing_lookback)
        elif bias == "BEARISH":
            return self._check_bearish_rb(df, initial, confirmation, fib_levels, swing_lookback)

        return None

    def _check_bullish_rb(
        self,
        df: pd.DataFrame,
        initial: pd.Series,
        confirmation: pd.Series,
        fib_levels: FibLevels,
        lookback: int,
    ) -> Optional[RejectionBlock]:
        """
        Check for a bullish rejection block (for LONG entries).

        Requirements:
        1. Initial candle is in the fib discount zone
        2. There was a liquidity sweep BELOW a recent swing low
        3. Confirmation candle closes BULLISH (close > open)
        """
        # Step 1: Confirmation candle must be bullish
        if confirmation["close"] <= confirmation["open"]:
            return None

        # Step 2: Initial candle must be in the discount zone (at or below 0.5 fib)
        candle_midpoint = (initial["high"] + initial["low"]) / 2
        fib_zone = fib_levels.get_zone(candle_midpoint)
        if fib_zone is None:
            return None  # Not in discount zone

        # Step 3: Check for liquidity sweep — wick below a recent swing low
        # ICT Concept: smart money sweeps sell-side liquidity (stop losses below lows)
        # before reversing. This is the "manipulation" that precedes the real move.
        #
        # We look for LOCAL swing lows (not the absolute minimum) in the lookback window.
        # A swing low = a candle whose low is lower than the candle before and after it.
        # The RB candle must wick BELOW at least one of these swing lows.
        recent = df.iloc[-(lookback + 2): -2]
        if len(recent) < 3:
            return None

        swing_lows = []
        for i in range(1, len(recent) - 1):
            if (recent["low"].iloc[i] <= recent["low"].iloc[i - 1]
                    and recent["low"].iloc[i] <= recent["low"].iloc[i + 1]):
                swing_lows.append(recent["low"].iloc[i])

        # Fallback: if no swing low found, use the lowest low in the window
        if not swing_lows:
            swing_lows = [recent["low"].min()]

        # The initial candle's wick must have gone below at least one swing low
        swept_level = None
        for sl in sorted(swing_lows, reverse=True):  # Check highest swing low first
            if initial["low"] < sl:
                swept_level = sl
                break

        if swept_level is None:
            return None

        logger.info(
            "Bullish RB: sweep below %.2f (candle low=%.2f), confirmed by bullish close",
            swept_level,
            initial["low"],
        )

        # Step 4: Calculate entry price
        block_range = initial["high"] - initial["low"]
        is_large = block_range > config.LARGE_RB_THRESHOLD

        if is_large:
            # Large block: use CE (50%) for tighter entry
            entry_price = initial["low"] + (block_range * 0.5)
            logger.info("Large block (%.1f pts) — using CE entry at %.2f", block_range, entry_price)
        else:
            # Standard: entry at the OPENING PRICE of the initial RB candle
            # Per Powell: "Entry placed at the opening price of the Rejection Block"
            # The RB IS the initial candle — NOT the confirmation candle.
            entry_price = initial["open"]

        rb = RejectionBlock(
            timestamp=df.index[-1],
            direction="LONG",
            entry_price=entry_price,
            block_high=initial["high"],
            block_low=initial["low"],
            block_range=block_range,
            manipulation_high=initial["low"],  # For longs, the swept low is our reference
            fib_zone=fib_zone,
            is_large=is_large,
        )

        self.last_detected = rb
        return rb

    def _check_bearish_rb(
        self,
        df: pd.DataFrame,
        initial: pd.Series,
        confirmation: pd.Series,
        fib_levels: FibLevels,
        lookback: int,
    ) -> Optional[RejectionBlock]:
        """
        Check for a bearish rejection block (for SHORT entries).

        Requirements:
        1. Initial candle is in the fib premium zone
        2. There was a liquidity sweep ABOVE a recent swing high
        3. Confirmation candle closes BEARISH (close < open)
        """
        # Step 1: Confirmation candle must be bearish
        if confirmation["close"] >= confirmation["open"]:
            return None

        # Step 2: Initial candle must be in the premium/discount zone (at or above 0.5 fib)
        candle_midpoint = (initial["high"] + initial["low"]) / 2
        fib_zone = fib_levels.get_zone(candle_midpoint)
        if fib_zone is None:
            return None

        # Step 3: Check for liquidity sweep — wick above a recent swing high
        # Mirror of the bullish logic: find local swing highs and check if
        # the initial candle wicked above at least one.
        recent = df.iloc[-(lookback + 2): -2]
        if len(recent) < 3:
            return None

        swing_highs = []
        for i in range(1, len(recent) - 1):
            if (recent["high"].iloc[i] >= recent["high"].iloc[i - 1]
                    and recent["high"].iloc[i] >= recent["high"].iloc[i + 1]):
                swing_highs.append(recent["high"].iloc[i])

        if not swing_highs:
            swing_highs = [recent["high"].max()]

        swept_level = None
        for sh in sorted(swing_highs):  # Check lowest swing high first
            if initial["high"] > sh:
                swept_level = sh
                break

        if swept_level is None:
            return None

        logger.info(
            "Bearish RB: sweep above %.2f (candle high=%.2f), confirmed by bearish close",
            swept_level,
            initial["high"],
        )

        # Step 4: Calculate entry price
        block_range = initial["high"] - initial["low"]
        is_large = block_range > config.LARGE_RB_THRESHOLD

        if is_large:
            # Large block: use CE or 25% level
            entry_price = initial["high"] - (block_range * 0.25)
            logger.info("Large block (%.1f pts) — using 25%% entry at %.2f", block_range, entry_price)
        else:
            # Standard: entry at the OPENING PRICE of the initial RB candle
            entry_price = initial["open"]

        rb = RejectionBlock(
            timestamp=df.index[-1],
            direction="SHORT",
            entry_price=entry_price,
            block_high=initial["high"],
            block_low=initial["low"],
            block_range=block_range,
            manipulation_high=initial["high"],  # For shorts, the swept high is our SL reference
            fib_zone=fib_zone,
            is_large=is_large,
        )

        self.last_detected = rb
        return rb
