"""
Fibonacci Retracement Module — draws OTE fibs on unbalanced legs.

ICT Concept: We don't just buy randomly in a trend. We wait for price to retrace
into a "discount" zone using Fibonacci levels drawn on the most recent UNBALANCED leg.

An "unbalanced leg" is one that has NOT yet retraced to its own 50% level — meaning
institutional order flow hasn't yet been mitigated.

Key Fibonacci Levels:
  - 0.5  = Equilibrium (minimum depth for a valid entry zone)
  - 0.62 = Optimal Trade Entry (OTE) — the sweet spot
  - 0.79 = Deep Discount — last chance before invalidation

Drawing Rules:
  - For LONGS: draw from the swing low to the high of the first bearish close after the leg
  - If price makes a new high before hitting discount, REDRAW from the new high
"""

import logging
from dataclasses import dataclass
from typing import Optional

import pandas as pd

import config

logger = logging.getLogger(__name__)


def _long_leg_valid(recent_low: float, swing_low: float, equilibrium: float) -> bool:
    """
    Decide whether a bullish fib leg is still tradeable.

    structural (default): the leg holds until its origin swing low is violated.
    Entries live in the 0.5-0.79 retracement zone, so the leg MUST be allowed
    to retrace past equilibrium — that retracement IS the entry condition.

    legacy: the original rule (recent_low > equilibrium). It marks the leg
    invalid the moment price reaches 0.5 — but the rejection block detector
    only accepts candles AT OR BELOW 0.5. The two conditions are mutually
    exclusive, so under legacy mode no ICT signal can ever fire.
    """
    if config.FIB_VALIDITY_MODE == "legacy":
        return recent_low > equilibrium
    return recent_low > swing_low


def _short_leg_valid(recent_high: float, swing_high: float, equilibrium: float) -> bool:
    """Mirror of _long_leg_valid for bearish legs."""
    if config.FIB_VALIDITY_MODE == "legacy":
        return recent_high < equilibrium
    return recent_high < swing_high


@dataclass
class FibLevels:
    """Stores the computed Fibonacci levels for the current setup."""

    swing_low: float
    swing_high: float
    equilibrium: float  # 0.5 retracement
    ote: float  # 0.62 retracement
    deep_discount: float  # 0.79 retracement
    direction: str  # "LONG" or "SHORT"
    is_valid: bool  # Whether the leg is still unbalanced

    def contains_price(self, price: float) -> bool:
        """Check if price is within the discount zone (>= 0.5 retracement)."""
        if self.direction == "LONG":
            # For longs, discount zone is BELOW equilibrium
            return price <= self.equilibrium
        else:
            # For shorts, premium zone is ABOVE equilibrium
            return price >= self.equilibrium

    def get_zone(self, price: float) -> Optional[str]:
        """Return which fib zone price is in, if any."""
        if self.direction == "LONG":
            if price <= self.deep_discount:
                return "deep_discount"
            elif price <= self.ote:
                return "ote"
            elif price <= self.equilibrium:
                return "equilibrium"
        else:
            if price >= self.deep_discount:
                return "deep_discount"
            elif price >= self.ote:
                return "ote"
            elif price >= self.equilibrium:
                return "equilibrium"
        return None


class FibonacciTracer:
    """
    Identifies unbalanced legs and computes Fibonacci retracement levels.

    Usage:
        tracer = FibonacciTracer()
        levels = tracer.compute(df_1h, bias="BULLISH")
        if levels and levels.contains_price(current_price):
            # We're in the discount zone — look for entry triggers
    """

    def __init__(self):
        self.current_levels: Optional[FibLevels] = None

    def compute(self, df: pd.DataFrame, bias: str) -> Optional[FibLevels]:
        """
        Find the most recent unbalanced leg and draw Fibonacci levels.

        Args:
            df: 1H OHLCV DataFrame (chronological).
            bias: "BULLISH" or "BEARISH" — determines fib direction.

        Returns:
            FibLevels if a valid unbalanced leg is found, else None.
        """
        if df.empty or len(df) < 10:
            return None

        if bias == "BULLISH":
            levels = self._compute_long_fibs(df)
        elif bias == "BEARISH":
            levels = self._compute_short_fibs(df)
        else:
            return None

        self.current_levels = levels
        return levels

    def _compute_long_fibs(self, df: pd.DataFrame) -> Optional[FibLevels]:
        """
        For BULLISH bias: find the most recent up-leg and draw fibs.

        ICT Rule:
        1. Find the swing low that started the most recent bullish leg
        2. Find the high of the FIRST BEARISH close after the leg
           (this marks where selling pressure first appeared)
        3. Draw fib from swing_low to that high
        4. The leg is "unbalanced" if price has NOT yet retraced to the 0.5 level
        """
        # Walk backwards to find the most recent significant swing low
        swing_low_idx = self._find_recent_swing_low(df)
        if swing_low_idx is None:
            return None

        swing_low = df["low"].iloc[swing_low_idx]

        # From the swing low, walk forward to find the first bearish close
        # after price has made a significant move up
        fib_high = None
        for i in range(swing_low_idx + 1, len(df)):
            candle = df.iloc[i]
            # Track the running high
            if fib_high is None or candle["high"] > fib_high:
                fib_high = candle["high"]

            # First bearish close after leg = where we anchor the fib top
            if candle["close"] < candle["open"] and fib_high is not None:
                break

        if fib_high is None or fib_high <= swing_low:
            return None

        # Check if leg is still unbalanced (price hasn't hit 0.5 yet)
        leg_range = fib_high - swing_low
        equilibrium = fib_high - (leg_range * 0.5)

        # Leg validity: structural mode = swing low unbroken; legacy = untouched 0.5
        recent_low = df["low"].iloc[-5:].min()
        is_valid = _long_leg_valid(recent_low, swing_low, equilibrium)

        if not is_valid:
            retracement_pct = (fib_high - recent_low) / leg_range * 100
            worst_candle_idx = df["low"].iloc[-5:].idxmin()
            logger.debug(
                "Fib invalid (LONG): leg=%.2f–%.2f range=%.2f | "
                "equilibrium=%.2f | recent_low=%.2f (candle %s) | "
                "retraced=%.1f%% — leg already balanced past 50%%",
                swing_low, fib_high, leg_range,
                equilibrium, recent_low, worst_candle_idx, retracement_pct,
            )

        # If price made a new high after the original fib_high, REDRAW
        actual_high = df["high"].iloc[swing_low_idx:].max()
        if actual_high > fib_high:
            old_fib_high = fib_high
            fib_high = actual_high
            leg_range = fib_high - swing_low
            equilibrium = fib_high - (leg_range * 0.5)
            recent_low = df["low"].iloc[-5:].min()
            is_valid = _long_leg_valid(recent_low, swing_low, equilibrium)
            logger.debug(
                "Fib LONG redrawn: old_high=%.2f → new_high=%.2f | "
                "new_range=%.2f new_EQ=%.2f valid=%s",
                old_fib_high, fib_high, leg_range, equilibrium, is_valid,
            )
            if not is_valid:
                retracement_pct = (fib_high - recent_low) / leg_range * 100
                logger.debug(
                    "Fib invalid after redraw (LONG): recent_low=%.2f retraced=%.1f%%",
                    recent_low, retracement_pct,
                )

        # Compute all levels
        ote = fib_high - (leg_range * 0.62)
        deep_discount = fib_high - (leg_range * 0.79)

        levels = FibLevels(
            swing_low=swing_low,
            swing_high=fib_high,
            equilibrium=equilibrium,
            ote=ote,
            deep_discount=deep_discount,
            direction="LONG",
            is_valid=is_valid,
        )

        logger.info(
            "Long Fibs: low=%.2f high=%.2f EQ=%.2f OTE=%.2f DD=%.2f valid=%s",
            swing_low, fib_high, equilibrium, ote, deep_discount, is_valid,
        )
        return levels

    def _compute_short_fibs(self, df: pd.DataFrame) -> Optional[FibLevels]:
        """
        For BEARISH bias: find the most recent down-leg and draw fibs.

        Mirror of long fibs:
        1. Find the swing high that started the bearish leg
        2. Find the low of the first bullish close after the leg
        3. Draw fib from swing_high down to that low
        """
        swing_high_idx = self._find_recent_swing_high(df)
        if swing_high_idx is None:
            return None

        swing_high = df["high"].iloc[swing_high_idx]

        # Walk forward to find the first bullish close after the down-leg
        fib_low = None
        for i in range(swing_high_idx + 1, len(df)):
            candle = df.iloc[i]
            if fib_low is None or candle["low"] < fib_low:
                fib_low = candle["low"]

            if candle["close"] > candle["open"] and fib_low is not None:
                break

        if fib_low is None or fib_low >= swing_high:
            return None

        leg_range = swing_high - fib_low

        # For shorts, fibs are drawn upward from the low
        equilibrium = fib_low + (leg_range * 0.5)

        # Leg validity: structural mode = swing high unbroken; legacy = untouched 0.5
        recent_high = df["high"].iloc[-5:].max()
        is_valid = _short_leg_valid(recent_high, swing_high, equilibrium)

        if not is_valid:
            retracement_pct = (recent_high - fib_low) / leg_range * 100
            worst_candle_idx = df["high"].iloc[-5:].idxmax()
            logger.debug(
                "Fib invalid (SHORT): leg=%.2f–%.2f range=%.2f | "
                "equilibrium=%.2f | recent_high=%.2f (candle %s) | "
                "retraced=%.1f%% — leg already balanced past 50%%",
                fib_low, swing_high, leg_range,
                equilibrium, recent_high, worst_candle_idx, retracement_pct,
            )

        # Redraw if new low was made
        actual_low = df["low"].iloc[swing_high_idx:].min()
        if actual_low < fib_low:
            old_fib_low = fib_low
            fib_low = actual_low
            leg_range = swing_high - fib_low
            equilibrium = fib_low + (leg_range * 0.5)
            recent_high = df["high"].iloc[-5:].max()
            is_valid = _short_leg_valid(recent_high, swing_high, equilibrium)
            logger.debug(
                "Fib SHORT redrawn: old_low=%.2f → new_low=%.2f | "
                "new_range=%.2f new_EQ=%.2f valid=%s",
                old_fib_low, fib_low, leg_range, equilibrium, is_valid,
            )
            if not is_valid:
                retracement_pct = (recent_high - fib_low) / leg_range * 100
                logger.debug(
                    "Fib invalid after redraw (SHORT): recent_high=%.2f retraced=%.1f%%",
                    recent_high, retracement_pct,
                )

        ote = fib_low + (leg_range * 0.62)
        deep_discount = fib_low + (leg_range * 0.79)

        levels = FibLevels(
            swing_low=fib_low,
            swing_high=swing_high,
            equilibrium=equilibrium,
            ote=ote,
            deep_discount=deep_discount,
            direction="SHORT",
            is_valid=is_valid,
        )

        logger.info(
            "Short Fibs: high=%.2f low=%.2f EQ=%.2f OTE=%.2f DD=%.2f valid=%s",
            swing_high, fib_low, equilibrium, ote, deep_discount, is_valid,
        )
        return levels

    @staticmethod
    def _find_recent_swing_low(df: pd.DataFrame, lookback: int = 5) -> Optional[int]:
        """Find the index of the most recent swing low."""
        for i in range(len(df) - lookback - 1, lookback, -1):
            window = df["low"].iloc[i - lookback : i + lookback + 1]
            if df["low"].iloc[i] == window.min():
                return i
        return None

    @staticmethod
    def _find_recent_swing_high(df: pd.DataFrame, lookback: int = 5) -> Optional[int]:
        """Find the index of the most recent swing high."""
        for i in range(len(df) - lookback - 1, lookback, -1):
            window = df["high"].iloc[i - lookback : i + lookback + 1]
            if df["high"].iloc[i] == window.max():
                return i
        return None
