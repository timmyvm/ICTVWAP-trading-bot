"""
Signal Engine — orchestrates entry detection across all three modes.

This module ties together bias, fibs, rejection blocks, and levels to produce
actionable trade signals. It implements the three entry modes:

Mode "1m":
  - Uses 1-minute candles for rejection block detection.
  - Tightest stops, highest R:R potential, but requires fast data.

Mode "5m":
  - Uses 5-minute candles for rejection block detection.
  - Stop loss: above manipulation high, CE of 5m block, or 0.79 fib level.
  - R:R must be between 1:3 and 1:6.

Mode "hybrid":
  - Wait for 5m RB confirmation first.
  - Then drop to 1m and wait for a 1m RB WITHIN the 5m zone.
  - Uses 1m entry price and 1m-level stop for even tighter risk.

WHY three modes:
  - 1m is precision sniping — great R:R but noisy
  - 5m is more reliable confirmation but wider stops
  - hybrid gives the best of both: 5m confirmation + 1m precision
"""

import logging
from dataclasses import dataclass
from datetime import datetime, time
from typing import Optional

import pandas as pd
import pytz

import config
from strategy.bias import HTFBias
from strategy.fibonacci import FibLevels, FibonacciTracer
from strategy.levels import KeyLevels
from strategy.rejection_block import RejectionBlock, RejectionBlockDetector

logger = logging.getLogger(__name__)

NY_TZ = pytz.timezone("America/New_York")


@dataclass
class TradeSignal:
    """A fully validated trade signal ready for execution."""

    direction: str  # "LONG" or "SHORT"
    entry_price: float
    stop_loss: float
    take_profit: float
    risk_reward: float
    mode: str  # "1m", "5m", or "hybrid"
    rb: RejectionBlock  # The rejection block that triggered this signal
    bias: str  # The HTF bias at time of signal
    fib_zone: str  # Which fib zone the entry is in
    tier: int = 1  # Tier 1 = premium (OTE/DD, R:R 1:5+), Tier 2 = confirmation (R:R 1:3+)
    setup_id: str = ""  # Identity of the fib leg — re-entries after a stop-out share it


class SignalEngine:
    """
    Evaluates market conditions and generates trade signals.

    Flow:
    1. Check HTF bias (must be directional, not NEUTRAL)
    2. Compute Fibonacci levels on 1H
    3. Check if price is in discount zone
    4. Scan for rejection blocks on entry timeframe
    5. Calculate SL/TP and validate R:R
    6. Output a TradeSignal if all conditions are met
    """

    def __init__(self):
        self.bias_engine = HTFBias()
        self.fib_tracer = FibonacciTracer()
        self.rb_detector = RejectionBlockDetector()
        self.key_levels = KeyLevels()

        # For hybrid mode: stores the 5m RB while waiting for 1m confirmation
        self._pending_5m_rb: Optional[RejectionBlock] = None

        # Judas Swing state: tracks if 10 AM manipulation was detected this session
        self._judas_detected_today: Optional[str] = None  # date string
        self._judas_direction: Optional[str] = None  # "BULLISH" or "BEARISH"

    def evaluate(
        self,
        df_1m: pd.DataFrame,
        df_5m: pd.DataFrame,
        df_15m: pd.DataFrame,
        df_1h: pd.DataFrame,
        df_4h: pd.DataFrame,
        current_price: float,
        now: Optional[datetime] = None,
    ) -> Optional[TradeSignal]:
        """
        Run the full signal evaluation pipeline.

        `now` is injectable so backtests can replay history; live callers omit it.

        Returns a TradeSignal if all conditions align, else None.
        """
        now_ny = now if now is not None else datetime.now(NY_TZ)

        # --- Step 0: Session filter ---
        # Powell V3: NY AM is preferred, London is valid only if HTF bias is strong.
        # Outside both sessions: no new entries.
        # Read allowed sessions from active_params() (testing mode allows more sessions)
        params = config.active_params()
        session = self._get_session(params.get("sessions", ["ny_am"]), now_ny)
        if session is None:
            logger.debug("Outside trading sessions — no signal")
            return None

        # --- Step 1: Determine HTF bias ---
        # We need to know if we're looking for longs or shorts BEFORE anything else.
        # Trading against the HTF bias is how retail traders get trapped.
        bias = self.bias_engine.evaluate(df_1h, df_4h, current_price)

        if bias == "NEUTRAL":
            logger.debug("Bias is NEUTRAL — no signal")
            return None

        # --- Step 1b: HTF trend alignment gate ---
        # A retrace structure-break mid-crash reads as BULLISH bias while the
        # broader 4H trend is still down — those counter-trend entries were
        # every losing long in the 180-day backtest. Trade with the cascade.
        if config.TREND_ALIGNMENT_FILTER:
            trend = self._htf_trend(df_4h)
            if trend is not None and trend != bias:
                logger.info(
                    "Trend gate: bias %s fights 4H trend %s — no signal",
                    bias, trend,
                )
                return None

        # In live mode with htf_bias_strict, require stronger confirmation
        if params.get("htf_bias_strict", False):
            logger.info("Strict bias mode — requiring clear HTF confirmation")

        # London session requires strong/clear bias — reject if NEUTRAL was close
        if session == "LONDON":
            logger.info("London session — proceeding only because HTF bias is clear (%s)", bias)

        # --- Step 0b: Judas Swing filter (NY AM only) ---
        # Powell V4: During NY AM, watch for the 10 AM manipulation ("Judas Swing").
        # Between 9:30 and 10:00, the market often fakes a move in one direction
        # (sweeping liquidity) before reversing. If require_10am_filter is True,
        # wait until after 10:00 AM to confirm the Judas move has played out.
        if session == "NY_AM" and params.get("require_10am_filter", False):
            if now_ny.hour == 9 or (now_ny.hour == 10 and now_ny.minute == 0):
                logger.info("Judas Swing window (9:30-10:00) — waiting for manipulation to complete")
                return None

            # After 10:00 AM: detect the Judas direction from the 9:30-10:00 move
            today_str = now_ny.strftime("%Y-%m-%d")
            if self._judas_detected_today != today_str:
                judas_dir = self._detect_judas_swing(df_1m, now_ny)
                if judas_dir:
                    self._judas_detected_today = today_str
                    self._judas_direction = judas_dir
                    logger.info("Judas Swing detected: fake %s move — expecting reversal", judas_dir)

            # Directional filter: a fake move UP implies the real move is DOWN,
            # so only trades aligned with the post-manipulation direction pass.
            if self._judas_detected_today == today_str and self._judas_direction:
                expected = "BEARISH" if self._judas_direction == "BULLISH" else "BULLISH"
                if bias != expected:
                    logger.info(
                        "Judas filter: fake %s move expects %s bias, have %s — no signal",
                        self._judas_direction, expected, bias,
                    )
                    return None

        # --- Step 2: Update key levels ---
        self.key_levels.update_session_opens(df_1m, now_ny)
        self.key_levels.scan_sus_candles(df_15m, "15m")
        self.key_levels.scan_sus_candles(df_4h, "4h")
        self.key_levels.scan_structural_levels(df_1h, df_4h)
        self.key_levels.check_nwog_filled(current_price)

        # Feed NWOG info back to bias engine for override logic.
        # Clearing on fill matters: without it the bias engine keeps a stale
        # NWOG level and stays force-BEARISH for the rest of the process life.
        if self.key_levels.nwog and not self.key_levels.nwog.filled:
            self.bias_engine.set_nwog(self.key_levels.nwog.ce)
        else:
            self.bias_engine.set_nwog(None)

        # --- Step 3: Compute Fibonacci levels ---
        fib_levels = self.fib_tracer.compute(df_1h, bias)
        if fib_levels is None or not fib_levels.is_valid:
            logger.debug("No valid fib levels — no signal")
            return None

        # --- Step 4: Check entry based on mode ---
        entry_mode = config.ENTRY_MODE

        if entry_mode == "1m":
            return self._evaluate_1m(df_1m, fib_levels, bias, current_price)
        elif entry_mode == "5m":
            return self._evaluate_5m(df_5m, fib_levels, bias, current_price)
        elif entry_mode == "hybrid":
            return self._evaluate_hybrid(df_1m, df_5m, fib_levels, bias, current_price)
        else:
            logger.error("Unknown ENTRY_MODE: %s", entry_mode)
            return None

    def _evaluate_1m(
        self,
        df_1m: pd.DataFrame,
        fib_levels: FibLevels,
        bias: str,
        current_price: float,
    ) -> Optional[TradeSignal]:
        """
        Mode "1m": scan 1-minute candles for rejection blocks.

        All standard RB rules apply. This gives the tightest entries
        but requires watching 1m chart noise.
        """
        rb = self.rb_detector.scan(df_1m, fib_levels, bias)
        if rb is None:
            return None

        return self._build_signal(rb, fib_levels, bias, current_price, mode="1m")

    def _evaluate_5m(
        self,
        df_5m: pd.DataFrame,
        fib_levels: FibLevels,
        bias: str,
        current_price: float,
    ) -> Optional[TradeSignal]:
        """
        Mode "5m": scan 5-minute candles for rejection blocks.

        Stop loss options (pick the most logical):
        - Above manipulation high (the swept liquidity point)
        - CE of the 5m block
        - 0.79 fib level

        R:R must be between 1:3 and 1:6 for 5m mode.
        """
        rb = self.rb_detector.scan(df_5m, fib_levels, bias)
        if rb is None:
            return None

        signal = self._build_signal(rb, fib_levels, bias, current_price, mode="5m")
        if signal is None:
            return None

        # 5m mode requires R:R between 3.0 and 6.0
        if not (3.0 <= signal.risk_reward <= 6.0):
            logger.info(
                "5m signal rejected: R:R %.2f not in [3.0, 6.0]",
                signal.risk_reward,
            )
            return None

        return signal

    def _evaluate_hybrid(
        self,
        df_1m: pd.DataFrame,
        df_5m: pd.DataFrame,
        fib_levels: FibLevels,
        bias: str,
        current_price: float,
    ) -> Optional[TradeSignal]:
        """
        Mode "hybrid": two-step confirmation.

        1. First, wait for a 5m RB to confirm (establishes the zone)
        2. Then drop to 1m and wait for a 1m RB WITHIN that 5m zone
        3. Use 1m entry and 1m-level stop for tighter risk

        WHY: The 5m RB gives us confidence that the level matters.
        The 1m RB gives us precision on entry and a much tighter stop.
        """
        # Check for new 5m RB
        rb_5m = self.rb_detector.scan(df_5m, fib_levels, bias)
        if rb_5m is not None:
            self._pending_5m_rb = rb_5m
            logger.info(
                "Hybrid: 5m RB confirmed at %.2f — waiting for 1m trigger",
                rb_5m.entry_price,
            )

        # If we have a pending 5m RB, look for 1m confirmation within it
        if self._pending_5m_rb is not None:
            rb_1m = self.rb_detector.scan(df_1m, fib_levels, bias)
            if rb_1m is not None:
                # Verify the 1m RB is within the 5m block's range
                within_zone = (
                    self._pending_5m_rb.block_low <= rb_1m.entry_price <= self._pending_5m_rb.block_high
                )
                if within_zone:
                    logger.info(
                        "Hybrid: 1m RB confirmed within 5m zone — triggering entry at %.2f",
                        rb_1m.entry_price,
                    )
                    self._pending_5m_rb = None  # Reset
                    return self._build_signal(rb_1m, fib_levels, bias, current_price, mode="hybrid")

            # Invalidate if price has moved too far from the 5m zone
            if bias == "BULLISH" and current_price > self._pending_5m_rb.block_high * 1.002:
                self._pending_5m_rb = None
                logger.info("Hybrid: 5m zone invalidated — price moved above block")
            elif bias == "BEARISH" and current_price < self._pending_5m_rb.block_low * 0.998:
                self._pending_5m_rb = None
                logger.info("Hybrid: 5m zone invalidated — price moved below block")

        return None

    def _build_signal(
        self,
        rb: RejectionBlock,
        fib_levels: FibLevels,
        bias: str,
        current_price: float,
        mode: str,
    ) -> Optional[TradeSignal]:
        """
        Build a complete TradeSignal from a confirmed rejection block.

        Calculates stop loss, take profit, and validates minimum R:R.
        """
        # Price-relative stop buffer (see STOP_BUFFER_PCT) with a small floor
        buffer = max(2.0, rb.entry_price * config.STOP_BUFFER_PCT / 100.0)

        if rb.direction == "LONG":
            # Stop loss: just below the manipulation low (the swept swing low)
            # Adding a buffer so we don't get clipped by a wick
            stop_loss = rb.manipulation_high - buffer

            # For 5m mode: stop must COVER the CE of the 5m block OR the 0.79 fib.
            # Per Powell V4: "place stop to cover the CE (50%) of the 5m candle, OR
            # the 0.79 Fibonacci level" — use the WIDEST (most protective) stop.
            # Logic: if price reaches these levels the trade thesis is truly invalidated.
            if mode == "5m":
                sl_options = [
                    stop_loss,
                    rb.block_low - buffer,  # Below the block
                    fib_levels.deep_discount - buffer,  # Below 0.79 fib
                ]
                # Use the WIDEST stop that's still below entry — most protective
                valid_sls = [s for s in sl_options if s < rb.entry_price]
                if valid_sls:
                    stop_loss = min(valid_sls)  # Widest = lowest (furthest from entry)

            # Take profit: nearest DOL target above entry that clears the
            # minimum distance (closer targets can't out-earn fees)
            dol = self.key_levels.get_nearest_dol(
                rb.entry_price, "LONG", config.MIN_TP_DISTANCE_PCT,
            )
            if dol is None:
                # Fallback: use fib swing high as target
                dol = fib_levels.swing_high
            take_profit = dol

        else:  # SHORT
            # Stop loss: just above the manipulation high (the swept swing high)
            stop_loss = rb.manipulation_high + buffer

            # For 5m shorts: use WIDEST stop (most protective), same logic as longs
            if mode == "5m":
                sl_options = [
                    stop_loss,
                    rb.block_high + buffer,
                    fib_levels.deep_discount + buffer,
                ]
                valid_sls = [s for s in sl_options if s > rb.entry_price]
                if valid_sls:
                    stop_loss = max(valid_sls)  # Widest = highest (furthest from entry)

            dol = self.key_levels.get_nearest_dol(
                rb.entry_price, "SHORT", config.MIN_TP_DISTANCE_PCT,
            )
            if dol is None:
                dol = fib_levels.swing_low
            take_profit = dol

        # The fib-swing fallback can still land inside the fee zone — final check
        min_tp_dist = rb.entry_price * config.MIN_TP_DISTANCE_PCT / 100.0
        if abs(take_profit - rb.entry_price) < min_tp_dist:
            logger.info(
                "Signal rejected: TP %.2f is < %.2f%% from entry — can't out-earn fees",
                take_profit, config.MIN_TP_DISTANCE_PCT,
            )
            return None

        # Calculate R:R
        risk = abs(rb.entry_price - stop_loss)
        reward = abs(take_profit - rb.entry_price)

        if risk == 0:
            logger.warning("Zero risk — invalid signal")
            return None

        rr = reward / risk

        # Validate minimum R:R
        if rr < config.MIN_RR:
            logger.info(
                "Signal rejected: R:R %.2f < minimum %.2f",
                rr,
                config.MIN_RR,
            )
            return None

        # Determine tier: Powell V3 two-tier model
        # Tier 1 = Premium entry at optimal fib (OTE or deeper), target R:R 1:5+
        # Tier 2 = Confirmation entry (equilibrium or missed premium), target R:R 1:3+
        tier = rb.tier  # Default from RB detection
        if rb.fib_zone in ("ote", "deep_discount"):
            tier = 1  # Premium zone = Tier 1
        else:
            tier = 2  # Equilibrium or shallower = Tier 2

        # Tier-specific minimum R:R check (toggleable — see ENFORCE_TIER_RR)
        if config.ENFORCE_TIER_RR:
            min_rr_for_tier = 5.0 if tier == 1 else 3.0
            if rr < min_rr_for_tier:
                logger.info(
                    "Signal rejected: Tier %d requires R:R >= %.1f, got %.2f",
                    tier, min_rr_for_tier, rr,
                )
                return None

        # Setup identity = the fib leg, NOT the individual RB. Re-entries after a
        # stop-out form a NEW rejection block on the same leg; keying by RB
        # timestamp would make every re-entry look like a fresh setup and reset
        # the re-entry budget.
        setup_id = f"{rb.direction}_{fib_levels.swing_low:.0f}_{fib_levels.swing_high:.0f}"

        signal = TradeSignal(
            direction=rb.direction,
            entry_price=rb.entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_reward=rr,
            mode=mode,
            rb=rb,
            bias=bias,
            fib_zone=rb.fib_zone,
            tier=tier,
            setup_id=setup_id,
        )

        logger.info(
            "SIGNAL: %s %s @ %.2f | SL=%.2f | TP=%.2f | R:R=%.2f | mode=%s | tier=%d",
            signal.direction,
            config.SYMBOL,
            signal.entry_price,
            signal.stop_loss,
            signal.take_profit,
            signal.risk_reward,
            mode,
            rb.tier,
        )
        return signal

    @staticmethod
    def _htf_trend(df_4h: pd.DataFrame) -> Optional[str]:
        """
        Broad 4H trend: last close vs SMA of the last TREND_SMA_PERIOD closes,
        with a neutral band (TREND_NEUTRAL_BAND_PCT) where no gate applies.

        Returns "BULLISH", "BEARISH", or None (flat / not enough data).
        """
        period = config.TREND_SMA_PERIOD
        if len(df_4h) < period:
            return None
        sma = df_4h["close"].iloc[-period:].mean()
        last = df_4h["close"].iloc[-1]
        band = config.TREND_NEUTRAL_BAND_PCT / 100.0
        if last > sma * (1 + band):
            return "BULLISH"
        if last < sma * (1 - band):
            return "BEARISH"
        return None

    @staticmethod
    def _get_session(
        allowed_sessions: list[str] | None = None,
        now: Optional[datetime] = None,
    ) -> Optional[str]:
        """
        Determine which trading session we're in.

        Powell V3: "Preferred session: New York AM. Also valid: London Session,
        provided HTF bias is strong."

        Args:
            allowed_sessions: list of allowed session keys, e.g. ["ny_am", "london"].
                              If None, defaults to ["ny_am"].
            now: injectable clock for backtesting (NY-tz aware).

        Returns:
            "NY_AM", "LONDON", or None (outside sessions = no trading)
        """
        if allowed_sessions is None:
            allowed_sessions = ["ny_am"]

        now_ny = now if now is not None else datetime.now(NY_TZ)
        current = now_ny.time()

        ny_start = time(config.NY_AM_SESSION[0], config.NY_AM_SESSION[1])
        ny_end = time(config.NY_AM_SESSION[2], config.NY_AM_SESSION[3])
        lon_start = time(config.LONDON_SESSION[0], config.LONDON_SESSION[1])
        lon_end = time(config.LONDON_SESSION[2], config.LONDON_SESSION[3])

        if "ny_am" in allowed_sessions and ny_start <= current <= ny_end:
            return "NY_AM"
        if "london" in allowed_sessions and lon_start <= current <= lon_end:
            return "LONDON"

        return None

    @staticmethod
    def _detect_judas_swing(
        df_1m: pd.DataFrame, now: Optional[datetime] = None,
    ) -> Optional[str]:
        """
        Detect the Judas Swing from the 9:30-10:00 AM NY window.

        The Judas Swing is a fake-out move at the NY session open that sweeps
        liquidity in one direction before the real move happens.

        Returns "BULLISH" if the 9:30-10:00 move was up (expect reversal down),
        "BEARISH" if the move was down (expect reversal up), or None.
        """
        if df_1m.empty:
            return None

        now_ny = now if now is not None else datetime.now(NY_TZ)
        today = now_ny.date()

        # Filter 1m candles from 9:30 to 10:00 today
        window_candles = []
        for ts, row in df_1m.iterrows():
            ts_ny = ts if ts.tzinfo else NY_TZ.localize(ts)
            if ts_ny.date() == today:
                t = ts_ny.time()
                if time(9, 30) <= t < time(10, 0):
                    window_candles.append(row)

        if len(window_candles) < 2:
            return None

        first_open = window_candles[0]["open"]
        last_close = window_candles[-1]["close"]
        window_high = max(c["high"] for c in window_candles)
        window_low = min(c["low"] for c in window_candles)

        # If the 9:30-10:00 move was predominantly up = BULLISH Judas (fake up, real down)
        # If predominantly down = BEARISH Judas (fake down, real up)
        move = last_close - first_open
        total_range = window_high - window_low

        if total_range == 0:
            return None

        # Need a meaningful move (at least 30% of window range)
        if abs(move) / total_range < 0.3:
            return None

        return "BULLISH" if move > 0 else "BEARISH"
