"""
VWAP Mean Reversion Signal Engine.

Generates trade signals when price extends significantly from VWAP and
conditions suggest a snap-back to fair value is imminent.

Strategy logic:
  - Only operates in RANGING regime (flat VWAP, normal ATR)
  - Watches for price to stretch to ±2 SD (or ±3 SD for premium entries)
  - Requires a LOW VOLUME extension candle (weak institutional conviction)
  - Requires a REVERSAL CONFIRMATION candle that closes back inside the band
  - Stop is placed 0.5 ATR beyond the band that was touched
  - Target is VWAP (fair value)
  - Breakeven: move stop to entry when price reaches ±1 SD band

Two setups per direction:
  Band-2 entries (±2 SD): minimum R:R 1:2
  Band-3 entries (±3 SD): minimum R:R 1:5 (premium, price is far from fair value)

Max 2 VWAP trades per session (resets at VWAP_SESSION_RESET_HOUR).
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import pandas as pd
import pytz

import config
from strategy.vwap import VWAPData, VWAPCalculator

logger = logging.getLogger(__name__)

NY_TZ = pytz.timezone("America/New_York")


@dataclass
class VWAPSignal:
    """A validated VWAP mean reversion trade signal."""

    direction: str          # "LONG" or "SHORT"
    entry_price: float      # Close of confirmation candle
    stop_loss: float        # 0.5 ATR beyond the touched band
    take_profit: float      # VWAP line
    risk_reward: float
    band: str               # Which band triggered: "lower_2", "lower_3", "upper_2", "upper_3"
    breakeven_price: float  # Price at which to move stop to entry (±1 SD band)

    # Match TradeSignal interface so execute_signal can handle both
    mode: str = "vwap"
    tier: int = 1           # Band-3 = tier 1 (premium), Band-2 = tier 2


class VWAPSignalEngine:
    """
    Scans for VWAP mean reversion setups on each candle close.

    Only fires when:
    1. Regime is RANGING
    2. Price recently touched a ±2 or ±3 SD band
    3. That extension candle had below-average volume (no strong breakout)
    4. A reversal candle has since closed back inside the band
    5. Stop distance is ≤ 1 ATR (tight, well-defined risk)
    6. R:R to VWAP is ≥ minimum (2:1 for band-2, 5:1 for band-3)
    7. Session trade limit not yet reached
    """

    def __init__(self):
        # Track how many VWAP trades have fired this session
        self._session_trade_count: int = 0
        self._current_session_date: Optional[str] = None

    def evaluate(
        self,
        df: pd.DataFrame,
        vwap_data: VWAPData,
        regime: str,
        now: Optional[datetime] = None,
    ) -> Optional[VWAPSignal]:
        """
        Check for a valid VWAP mean reversion signal on the current candle.

        Args:
            df:         5m (or 1m) OHLCV DataFrame, indexed by NY time.
            vwap_data:  Freshly computed VWAP data for this session.
            regime:     Current market regime from RegimeDetector.
            now:        injectable clock for backtesting (NY-tz aware).

        Returns:
            VWAPSignal if all conditions are met, else None.
        """
        # --- Guard: Only trade in ranging markets ---
        if regime != "RANGING":
            logger.debug("VWAP: skipping — regime is %s", regime)
            return None

        if vwap_data is None or len(df) < 5:
            return None

        # --- Guard: Session warm-up ---
        # With only a handful of candles since the midnight reset, the std bands
        # hug price and every wiggle "touches ±2σ". Wait for real bands.
        if vwap_data.session_candles < config.VWAP_MIN_SESSION_CANDLES:
            logger.debug(
                "VWAP: warm-up (%d/%d session candles)",
                vwap_data.session_candles, config.VWAP_MIN_SESSION_CANDLES,
            )
            return None

        # --- Guard: Session trade limit ---
        self._refresh_session_counter(now)
        if self._session_trade_count >= config.MAX_VWAP_TRADES_PER_SESSION:
            logger.debug(
                "VWAP: session limit reached (%d/%d)",
                self._session_trade_count,
                config.MAX_VWAP_TRADES_PER_SESSION,
            )
            return None

        # --- Compute ATR for stop sizing ---
        atr = VWAPCalculator._compute_atr(df)

        # --- Check long and short setups ---
        signal = self._check_long(df, vwap_data, atr)
        if signal is None:
            signal = self._check_short(df, vwap_data, atr)

        if signal:
            logger.info(
                "[VWAP] SIGNAL: %s @ %.2f | SL=%.2f | TP=%.2f (VWAP) | "
                "R:R=%.2f | band=%s | BE@%.2f",
                signal.direction,
                signal.entry_price,
                signal.stop_loss,
                signal.take_profit,
                signal.risk_reward,
                signal.band,
                signal.breakeven_price,
            )

        return signal

    def record_trade(self, now: Optional[datetime] = None):
        """Call after a VWAP trade is executed to increment the session counter."""
        self._refresh_session_counter(now)
        self._session_trade_count += 1
        logger.info(
            "VWAP: session trade count %d/%d",
            self._session_trade_count,
            config.MAX_VWAP_TRADES_PER_SESSION,
        )

    def _check_long(
        self,
        df: pd.DataFrame,
        vwap: VWAPData,
        atr: float,
    ) -> Optional[VWAPSignal]:
        """
        Check for a long setup at the lower_2 or lower_3 band.

        Pattern (reading the last few candles):
          1. An earlier candle (1-3 bars back) touched/broke below the band
             — that's the "extension candle" reaching for liquidity below VWAP
          2. That extension candle had LOW VOLUME (< 1.5x avg) — not a real breakdown
          3. The current candle (confirmation) has closed ABOVE the band
             — price has snapped back, confirming the band held
          4. Entry = close of confirmation candle (we know the band has been respected)
          5. Stop = band_level - 0.5 * ATR (a little below the rejection zone)
          6. TP = VWAP (price snaps back to fair value)
        """
        current = df.iloc[-1]

        # Check band-2 first (more common), then band-3 (premium)
        band_configs = [
            (vwap.lower_2, "lower_2", 2.0, 2),   # band, name, min_rr, tier
            (vwap.lower_3, "lower_3", 5.0, 1),
        ]

        for band_level, band_name, min_rr, tier in band_configs:
            # Scan recent candles for the extension candle
            # Look up to 3 bars back (don't go stale beyond that)
            for lookback in range(1, 4):
                if lookback >= len(df):
                    break

                ext_candle = df.iloc[-(lookback + 1)]

                # Extension candle must have touched or broken below the band
                if ext_candle["low"] > band_level:
                    continue

                # Extension candle volume must be BELOW threshold — weak breakdown
                # High volume = real institutional selling, not a mean reversion setup
                if ext_candle["volume"] >= vwap.vol_avg * config.VWAP_VOLUME_THRESHOLD:
                    logger.debug(
                        "VWAP long %s: extension candle volume too high "
                        "(%.0f vs threshold %.0f)",
                        band_name,
                        ext_candle["volume"],
                        vwap.vol_avg * config.VWAP_VOLUME_THRESHOLD,
                    )
                    continue

                # Confirmation candle must close ABOVE the band — rejection confirmed
                if current["close"] <= band_level:
                    continue

                # --- Build signal ---
                entry = current["close"]
                # Stop: 0.5 ATR below the band (safely below the rejection zone)
                sl = band_level - (0.5 * atr)
                stop_dist = entry - sl

                if stop_dist <= 0:
                    continue

                # Stop distance must be within 1 ATR (tight, defined risk)
                if stop_dist > config.VWAP_MAX_STOP_ATR * atr:
                    logger.debug(
                        "VWAP long %s: stop too wide (%.2f > %.2f ATR)",
                        band_name, stop_dist, config.VWAP_MAX_STOP_ATR * atr,
                    )
                    continue

                # TP = VWAP (fair value)
                tp = vwap.vwap
                reward = tp - entry

                if reward <= 0:
                    # Price is already above VWAP — no room for the trade
                    continue

                rr = reward / stop_dist

                if rr < min_rr:
                    logger.debug(
                        "VWAP long %s: R:R %.2f below minimum %.2f",
                        band_name, rr, min_rr,
                    )
                    continue

                # Breakeven: move stop to entry when price reaches -1 SD band
                # (price has recovered halfway back toward VWAP — lock in no-loss)
                breakeven_price = vwap.lower_1

                return VWAPSignal(
                    direction="LONG",
                    entry_price=round(entry, 2),
                    stop_loss=round(sl, 2),
                    take_profit=round(tp, 2),
                    risk_reward=round(rr, 2),
                    band=band_name,
                    breakeven_price=round(breakeven_price, 2),
                    mode="vwap",
                    tier=tier,
                )

        return None

    def _check_short(
        self,
        df: pd.DataFrame,
        vwap: VWAPData,
        atr: float,
    ) -> Optional[VWAPSignal]:
        """
        Check for a short setup at the upper_2 or upper_3 band.

        Mirror of _check_long — price extends above fair value, low volume,
        then snaps back below the band.
        """
        current = df.iloc[-1]

        band_configs = [
            (vwap.upper_2, "upper_2", 2.0, 2),
            (vwap.upper_3, "upper_3", 5.0, 1),
        ]

        for band_level, band_name, min_rr, tier in band_configs:
            for lookback in range(1, 4):
                if lookback >= len(df):
                    break

                ext_candle = df.iloc[-(lookback + 1)]

                # Extension candle must have pushed above the band
                if ext_candle["high"] < band_level:
                    continue

                # Low volume extension — weak breakout, likely to reverse
                if ext_candle["volume"] >= vwap.vol_avg * config.VWAP_VOLUME_THRESHOLD:
                    logger.debug(
                        "VWAP short %s: extension candle volume too high "
                        "(%.0f vs threshold %.0f)",
                        band_name,
                        ext_candle["volume"],
                        vwap.vol_avg * config.VWAP_VOLUME_THRESHOLD,
                    )
                    continue

                # Confirmation candle closes BELOW the band — rejection confirmed
                if current["close"] >= band_level:
                    continue

                # --- Build signal ---
                entry = current["close"]
                # Stop: 0.5 ATR above the band
                sl = band_level + (0.5 * atr)
                stop_dist = sl - entry

                if stop_dist <= 0:
                    continue

                # Stop distance must be within 1 ATR
                if stop_dist > config.VWAP_MAX_STOP_ATR * atr:
                    logger.debug(
                        "VWAP short %s: stop too wide (%.2f > %.2f ATR)",
                        band_name, stop_dist, config.VWAP_MAX_STOP_ATR * atr,
                    )
                    continue

                # TP = VWAP
                tp = vwap.vwap
                reward = entry - tp

                if reward <= 0:
                    continue

                rr = reward / stop_dist

                if rr < min_rr:
                    logger.debug(
                        "VWAP short %s: R:R %.2f below minimum %.2f",
                        band_name, rr, min_rr,
                    )
                    continue

                # Breakeven: move stop to entry when price falls to +1 SD band
                breakeven_price = vwap.upper_1

                return VWAPSignal(
                    direction="SHORT",
                    entry_price=round(entry, 2),
                    stop_loss=round(sl, 2),
                    take_profit=round(tp, 2),
                    risk_reward=round(rr, 2),
                    band=band_name,
                    breakeven_price=round(breakeven_price, 2),
                    mode="vwap",
                    tier=tier,
                )

        return None

    def _refresh_session_counter(self, now: Optional[datetime] = None):
        """Reset trade counter if we've crossed into a new session."""
        now_ny = now if now is not None else datetime.now(NY_TZ)
        # Session key = date + reset hour (e.g. "2026-03-16-00")
        session_key = now_ny.strftime("%Y-%m-%d") + f"-{config.VWAP_SESSION_RESET_HOUR:02d}"

        if self._current_session_date != session_key:
            if self._current_session_date is not None:
                logger.info(
                    "VWAP: new session — resetting trade counter (was %d)",
                    self._session_trade_count,
                )
            self._current_session_date = session_key
            self._session_trade_count = 0

