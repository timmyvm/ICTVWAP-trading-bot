"""
Powell Trades ICT Bot — Main Loop.

This is the entry point. The bot runs continuously, checking for new candle
closes across all timeframes and running the strategy pipeline when conditions
are met.

Architecture:
  1. Fetch candles across all timeframes
  2. On each new candle close, run the relevant checks:
     - 1m/5m: entry signal detection (rejection blocks)
     - 15m: sus candle scan
     - 1h: fibonacci retracement + bias update
     - 4h: bias update + sus candle scan
  3. If a valid signal fires, calculate risk and execute
  4. Log everything, handle errors gracefully, shut down cleanly

The bot is designed to be left running — it sleeps between checks
and handles KeyboardInterrupt for clean shutdown.
"""

import logging
import os
import sys
import time
from datetime import datetime

import pandas as pd
import pytz

import config
from data.feed import DataFeed
from execution.orders import OrderManager
from execution.risk import RiskManager
from strategy.levels import ATRModeSwitcher
from strategy.regime import RegimeDetector
from strategy.signals import SignalEngine
from strategy.vwap import VWAPCalculator
from strategy.vwap_signals import VWAPSignalEngine

# --- Logging Setup ---
# logs/ is gitignored — without this a fresh clone crashes on the FileHandler
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/bot.log"),
    ],
)
logger = logging.getLogger("main")
logging.getLogger("strategy.fibonacci").setLevel(logging.DEBUG)

NY_TZ = pytz.timezone("America/New_York")

# Candle intervals and their durations in seconds for sleep timing
INTERVAL_SECONDS = {
    "1": 60,
    "5": 300,
    "15": 900,
    "60": 3600,
    "240": 14400,
}


class TradingBot:
    """
    Main bot class that orchestrates the trading loop.

    On each iteration:
    1. Fetch fresh candle data
    2. Run the signal engine
    3. Execute valid signals (or paper trade)
    4. Sleep until the next candle close
    """

    def __init__(self):
        self.feed = DataFeed()
        self.signal_engine = SignalEngine()
        self.risk_manager = RiskManager()
        self.order_manager = OrderManager()
        self.atr_switcher = ATRModeSwitcher()

        # VWAP strategy components
        self.vwap_calculator = VWAPCalculator()
        self.regime_detector = RegimeDetector()
        self.vwap_signal_engine = VWAPSignalEngine()

        # Track the last processed candle timestamp per timeframe
        # to avoid re-processing the same candle
        self._last_candle_ts: dict[str, object] = {}

        # Re-entry state: tracks the current setup for re-entry after stop-outs.
        # Per Powell: if stopped out at 0.5, look for new RB at 0.62, then 0.79.
        # Max 2 re-entries per setup.
        self._active_setup_id: str | None = None
        self._was_stopped_out: bool = False

        # VWAP trade state: breakeven tracking for open VWAP positions
        self._vwap_breakeven_price: float | None = None   # Price to trigger breakeven move
        self._vwap_trade_direction: str | None = None     # Direction of open VWAP trade
        self._vwap_entry_price: float | None = None       # Entry — where the stop moves to

    def run(self):
        """Main loop — runs until interrupted."""
        params = config.active_params()
        logger.info("=" * 60)
        logger.info("Powell Trades Bot starting — ICT + VWAP strategies")
        logger.info("Testing mode: %s", config.TESTING_MODE)
        logger.info("Symbols: %s", params.get("symbols", [config.SYMBOL]))
        logger.info("Entry mode: %s", config.ENTRY_MODE)
        logger.info("Paper trade: %s", config.PAPER_TRADE)
        logger.info("Risk per trade: %s%%", config.RISK_PER_TRADE_PCT)
        logger.info("Min R:R: %s", config.MIN_RR)
        logger.info("Max daily trades (shared): %s", config.MAX_DAILY_TRADES)
        logger.info("Sessions: %s", params.get("sessions", ["ny_am"]))
        logger.info("[ICT]  Entry mode: %s | Min R:R: %s", config.ENTRY_MODE, config.MIN_RR)
        logger.info(
            "[VWAP] Slope threshold: %s | Vol threshold: %sx | Max stops: %s ATR | Session limit: %s",
            config.VWAP_SLOPE_THRESHOLD,
            config.VWAP_VOLUME_THRESHOLD,
            config.VWAP_MAX_STOP_ATR,
            config.MAX_VWAP_TRADES_PER_SESSION,
        )
        logger.info("=" * 60)

        # Load news levels from config into DOL targets
        self.signal_engine.key_levels.load_news_levels()

        # Update NWOG on startup (needs historical 1m data spanning the weekend)
        self._update_nwog()

        try:
            while True:
                self._tick()
                # Sleep based on entry mode — check every candle close
                sleep_interval = INTERVAL_SECONDS.get(
                    config.TIMEFRAME_MAP.get(config.ENTRY_MODE, "5"),
                    60,
                )
                # For hybrid mode, we need to check 1m candles
                if config.ENTRY_MODE == "hybrid":
                    sleep_interval = 60

                # Use shorter sleep with periodic wake-ups to stay responsive
                self._sleep_with_interrupt(sleep_interval)

        except KeyboardInterrupt:
            logger.info("Shutdown requested — cleaning up...")
            self.order_manager.cancel_open_orders()
            logger.info("Bot stopped gracefully.")

    def _tick(self):
        """
        Single iteration of the main loop.

        Fetches all candle data, checks for new closes, and runs the signal engine.
        """
        now_ny = datetime.now(NY_TZ)
        logger.debug("Tick at %s NY", now_ny.strftime("%H:%M:%S"))

        # --- Fetch candle data ---
        # 1m depth of 1000 (~16h) so the midnight and 10 AM opens are still in
        # the window during the NY AM session — 200 candles only spans 3.3h,
        # which silently dropped both DOL levels for most of the day.
        try:
            df_1m = self.feed.get_candles_by_tf("1m", limit=1000)
            df_5m = self.feed.get_candles_by_tf("5m", limit=200)
            df_15m = self.feed.get_candles_by_tf("15m", limit=100)
            df_1h = self.feed.get_candles_by_tf("1h", limit=100)
            df_4h = self.feed.get_candles_by_tf("4h", limit=100)
            df_1d = self.feed.get_candles_by_tf("1d", limit=60)
        except Exception as e:
            logger.error("Data fetch failed: %s", e)
            return

        # Validate we got data
        if any(df.empty for df in [df_1m, df_5m, df_1h, df_4h]):
            logger.warning("Missing candle data — skipping tick")
            return

        # --- Check for new candle closes ---
        # Only run the signal engine when we detect a new candle has closed.
        # This prevents processing the same candle multiple times.
        entry_tf = config.ENTRY_MODE if config.ENTRY_MODE != "hybrid" else "1m"
        entry_interval = config.TIMEFRAME_MAP.get(entry_tf, "5")
        entry_df = df_1m if entry_tf == "1m" else df_5m

        if entry_df.empty:
            return

        latest_ts = entry_df.index[-1]
        if entry_interval in self._last_candle_ts:
            if latest_ts <= self._last_candle_ts[entry_interval]:
                return  # No new candle — skip

        self._last_candle_ts[entry_interval] = latest_ts
        logger.debug("New %s candle closed at %s", entry_tf, latest_ts)

        # --- Update levels on 15m and 4h closes ---
        self._check_htf_updates(df_15m, "15m", "15")
        self._check_htf_updates(df_4h, "4h", "240")

        # --- ATR auto mode switching ---
        # Always evaluate ATR conditions so the bot can switch into AND out of any mode.
        recommended_mode = self.atr_switcher.evaluate(df_5m)
        if recommended_mode != config.ENTRY_MODE:
            logger.info(
                "ATR switcher recommends %s mode (was %s)",
                recommended_mode, config.ENTRY_MODE,
            )
            config.ENTRY_MODE = recommended_mode

        # --- Get current price ---
        current_price = self.feed.get_mark_price()
        if current_price is None:
            logger.warning("Could not fetch mark price — skipping tick")
            return

        # --- Check open positions for stop-out / TP hit ---
        self._check_position_status(current_price)

        # --- Check if we can trade ---
        can_trade, reason = self.risk_manager.can_trade()
        if not can_trade:
            logger.info("Trade blocked: %s", reason)
            return

        # ── ICT STRATEGY ─────────────────────────────────────────────────────
        signal = self.signal_engine.evaluate(
            df_1m=df_1m,
            df_5m=df_5m,
            df_15m=df_15m,
            df_1h=df_1h,
            df_4h=df_4h,
            current_price=current_price,
            df_1d=df_1d,
        )

        if signal is not None:
            # --- Re-entry budget check ---
            # Per Powell: after a stop-out, up to 2 re-entries on the SAME fib leg
            # (0.62 then 0.79). The budget is only consumed when a re-entry trade
            # actually executes — checking it every tick used to burn the whole
            # budget within minutes of a stop-out, before any trade could happen.
            if self._was_stopped_out and self._active_setup_id == signal.setup_id:
                can_re, target = self.risk_manager.can_re_enter(signal.setup_id)
                if not can_re:
                    logger.info(
                        "Re-entry exhausted for setup %s — skipping signal", signal.setup_id,
                    )
                    signal = None
                else:
                    logger.info("Re-entry signal on setup %s (%s)", signal.setup_id, target)

        if signal is not None:
            # --- Execute ICT signal ---
            balance = self.feed.get_account_balance()
            if balance is None or balance <= 0:
                logger.error("Could not fetch account balance — skipping ICT trade")
            else:
                qty = self.risk_manager.calculate_position_size(
                    account_balance=balance,
                    entry_price=signal.entry_price,
                    stop_loss=signal.stop_loss,
                )
                if qty <= 0:
                    logger.warning("ICT position size is zero — skipping trade")
                else:
                    success = self.order_manager.execute_signal(signal, qty, strategy="ICT")
                    if success:
                        self.risk_manager.record_trade()
                        self.risk_manager.record_re_entry(signal.setup_id)
                        self._active_setup_id = signal.setup_id
                        self._was_stopped_out = False
                    return  # Don't also check VWAP on the same candle as an ICT trade

        # ── VWAP STRATEGY ────────────────────────────────────────────────────
        # Runs independently on every tick. Uses 5m data for band calculations.
        # Will not fire if daily trade limit was already reached by ICT.
        if config.VWAP_ENABLED:
            self._tick_vwap(df_5m, current_price)

    def _tick_vwap(self, df_5m: pd.DataFrame, current_price: float):
        """
        Run the VWAP mean reversion strategy on the current candle.

        1. Compute fresh VWAP data for today's session
        2. Detect current regime (RANGING / TRENDING / NEWS)
        3. Check for VWAP signal (only fires in RANGING)
        4. Execute if valid and daily limit not reached
        5. Check VWAP breakeven for any open VWAP position
        """
        # --- Compute VWAP ---
        vwap_data = self.vwap_calculator.compute(df_5m)
        if vwap_data is None:
            logger.debug("VWAP: no data yet for today's session")
            return

        # --- Detect regime ---
        regime = self.regime_detector.get_regime(vwap_data, df_5m)

        # --- Check VWAP breakeven for any open VWAP position ---
        if self._vwap_breakeven_price is not None:
            should_move_be = False
            if self._vwap_trade_direction == "LONG" and current_price >= self._vwap_breakeven_price:
                should_move_be = True
            elif self._vwap_trade_direction == "SHORT" and current_price <= self._vwap_breakeven_price:
                should_move_be = True

            if should_move_be:
                logger.info(
                    "[VWAP] Breakeven triggered — price %.2f reached %.2f (%s)",
                    current_price,
                    self._vwap_breakeven_price,
                    "lower_1" if self._vwap_trade_direction == "LONG" else "upper_1",
                )
                # Move stop to the ENTRY price. Moving it to current_price (the
                # ±1σ band) parked the stop right where price oscillates on its
                # way to VWAP, wicking winners out for scratch losses.
                be_stop = (
                    self._vwap_entry_price
                    if self._vwap_entry_price is not None
                    else current_price
                )
                self.order_manager.modify_stop_loss("vwap_position", be_stop)
                self._vwap_breakeven_price = None  # Reset — only move once

        # --- Check if we can trade ---
        can_trade, reason = self.risk_manager.can_trade()
        if not can_trade:
            logger.debug("VWAP: trade blocked — %s", reason)
            return

        # --- Evaluate VWAP signal ---
        vwap_signal = self.vwap_signal_engine.evaluate(df_5m, vwap_data, regime)
        if vwap_signal is None:
            return

        # --- Execute VWAP signal ---
        balance = self.feed.get_account_balance()
        if balance is None or balance <= 0:
            logger.error("Could not fetch account balance — skipping VWAP trade")
            return

        qty = self.risk_manager.calculate_position_size(
            account_balance=balance,
            entry_price=vwap_signal.entry_price,
            stop_loss=vwap_signal.stop_loss,
        )

        if qty <= 0:
            logger.warning("VWAP position size is zero — skipping trade")
            return

        success = self.order_manager.execute_signal(vwap_signal, qty, strategy="VWAP")
        if success:
            self.risk_manager.record_trade()
            self.vwap_signal_engine.record_trade()
            # Arm breakeven tracking for this VWAP position
            self._vwap_breakeven_price = vwap_signal.breakeven_price
            self._vwap_trade_direction = vwap_signal.direction
            self._vwap_entry_price = vwap_signal.entry_price

    def _check_position_status(self, current_price: float):
        """
        Check if any open position has hit its SL or TP.

        For live trading, this queries Bybit's position API.
        For paper trading, it checks the last trade in CSV against current price.
        This enables:
        - Updating CSV result/PnL columns
        - Triggering re-entry logic after a stop-out
        - Moving stop to breakeven after significant move
        """
        if config.PAPER_TRADE or config.BYBIT_TESTNET:
            # In paper mode OR testnet: track positions via CSV, not the API.
            # Testnet API keys often have auth issues; CSV is the source of truth.
            result = self.order_manager.check_paper_position(current_price)
            if result == "STOPPED":
                self._was_stopped_out = True
                # Clear VWAP position tracking on any stop-out
                self._vwap_breakeven_price = None
                self._vwap_trade_direction = None
                self._vwap_entry_price = None
                logger.info("Paper position stopped out at %.2f — re-entry logic armed", current_price)
            elif result == "TP_HIT":
                self._was_stopped_out = False
                self._active_setup_id = None
                self._vwap_breakeven_price = None
                self._vwap_trade_direction = None
                self._vwap_entry_price = None
                logger.info("Paper position hit TP at %.2f", current_price)
        else:
            # Live mode: check if position still exists via Bybit API
            try:
                resp = self.feed.session.get_positions(
                    category=config.CATEGORY,
                    symbol=config.SYMBOL,
                )
                positions = resp.get("result", {}).get("list", [])
                has_position = any(float(p.get("size", 0)) > 0 for p in positions)
                if not has_position and self._active_setup_id:
                    # Position was closed (likely by SL or TP)
                    self._was_stopped_out = True
                    logger.info("Live position closed — re-entry logic armed")
            except Exception as e:
                logger.error("Failed to check position status: %s", e)

    def _check_htf_updates(self, df: pd.DataFrame, tf_label: str, interval: str):
        """Check if a new HTF candle closed and run sus candle scan."""
        if df.empty:
            return

        latest_ts = df.index[-1]
        if interval in self._last_candle_ts:
            if latest_ts <= self._last_candle_ts[interval]:
                return

        self._last_candle_ts[interval] = latest_ts
        self.signal_engine.key_levels.scan_sus_candles(df, tf_label)
        logger.debug("Updated %s levels at %s", tf_label, latest_ts)

    def _update_nwog(self):
        """
        Calculate NWOG on startup using targeted historical 1m data.

        The anchors are Friday 16:59 NY close and Sunday 18:00 NY open. A plain
        limit=200 fetch only covers ~3.3 hours, so unless the bot happened to
        boot on Sunday evening it could never see both anchors and NWOG was
        silently never set. get_weekend_candles_1m() fetches the two anchor
        windows directly.
        """
        logger.info("Calculating NWOG from historical data...")
        df_1m = self.feed.get_weekend_candles_1m()
        if not df_1m.empty:
            self.signal_engine.key_levels.update_nwog(df_1m)
            nwog = self.signal_engine.key_levels.nwog
            if nwog:
                logger.info("NWOG loaded: CE=%.2f (%s gap)", nwog.ce, nwog.direction)

                # Set NWOG override in bias engine
                if not nwog.filled:
                    self.signal_engine.bias_engine.set_nwog(nwog.ce)
            else:
                logger.info("No NWOG found in recent data")

    @staticmethod
    def _sleep_with_interrupt(seconds: int):
        """
        Sleep in small increments so KeyboardInterrupt is caught quickly.
        """
        for _ in range(seconds):
            time.sleep(1)


if __name__ == "__main__":
    bot = TradingBot()
    bot.run()
