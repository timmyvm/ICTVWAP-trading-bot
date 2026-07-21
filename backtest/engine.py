"""
Event-driven backtest engine for the Powell Trades bot.

Reuses the REAL strategy stack — SignalEngine (bias, fibs, rejection blocks,
key levels), VWAPCalculator, RegimeDetector, VWAPSignalEngine, RiskManager,
ATRModeSwitcher — by feeding them windowed frames and an injected clock, and
replaces only the exchange with a simulator:

  * walks the 1m stream; strategy ticks fire on entry-timeframe closes with the
    same cadence as main.py (1m/hybrid -> every minute, 5m -> every 5 minutes)
  * frame windows mirror the live fetch limits (1m x1000, 5m x200, HTF x100)
    and contain only CLOSED candles
  * ICT entries are limit orders that must actually be touched to fill
    (maker fee); unfilled orders expire after `order_ttl_min`
  * VWAP entries are market orders filled at the NEXT 1m open (taker fee +
    slippage) — no lookahead
  * SL/TP resolve intrabar on 1m candles; if both are inside one candle the
    STOP wins (conservative); take-profits never fill on the entry candle
  * fees and slippage are charged per config; position sizing via RiskManager

Known divergences from live (documented, deliberate):
  * one concurrent position per strategy; a new ICT signal replaces a pending
    unfilled order (live would stack GTC orders — see report)
  * ICT breakeven management is not simulated (main.py never wired it either)
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd
import pytz

import config
from execution.risk import RiskManager
from strategy.levels import ATRModeSwitcher, NWOG
from strategy.regime import RegimeDetector
from strategy.signals import SignalEngine
from strategy.vwap import VWAPCalculator
from strategy.vwap_signals import VWAPSignalEngine

logger = logging.getLogger(__name__)

NY_TZ = pytz.timezone("America/New_York")

WINDOW_LIMITS = {"1m": 1000, "5m": 200, "15m": 100, "1h": 100, "4h": 100}
TF_SECONDS = {"1m": 60, "5m": 300, "15m": 900, "1h": 3600, "4h": 14400}


@dataclass
class Position:
    strategy: str  # "ICT" | "VWAP"
    direction: str  # "LONG" | "SHORT"
    qty: float
    entry_price: float
    stop_loss: float
    take_profit: float
    entry_fee: float
    opened_at: pd.Timestamp
    entry_kind: str  # "maker" | "taker"
    meta: dict = field(default_factory=dict)
    be_trigger: Optional[float] = None
    be_target: Optional[float] = None
    be_done: bool = False
    fill_candle: Optional[pd.Timestamp] = None  # candle the fill happened in


@dataclass
class PendingLimit:
    signal: object  # TradeSignal
    qty: float
    placed_at: pd.Timestamp
    expires_at: pd.Timestamp


# NOTE ON FILL STYLE: the rulebook is explicit — "Always use LIMIT orders for
# entry... Taker orders at this account size will destroy profitability" — and
# execution/orders.py does place limit orders for both strategies. Entries
# therefore fill as resting limits (maker) that price must come back to, and
# take-profits fill as resting limits too; only stop-losses pay taker+slippage.


class BacktestEngine:
    def __init__(
        self,
        frames: dict[str, pd.DataFrame],
        start_balance: float = 10_000.0,
        order_ttl_min: int = 60,
        legacy_breakeven: bool = False,
        name: str = "backtest",
    ):
        self.frames = frames
        self.balance = start_balance
        self.start_balance = start_balance
        self.order_ttl_min = order_ttl_min
        self.legacy_breakeven = legacy_breakeven
        self.name = name

        # Strategy stack — the real thing
        self.signal_engine = SignalEngine()
        self.risk = RiskManager()
        self.atr_switcher = ATRModeSwitcher()
        self.vwap_calc = VWAPCalculator()
        self.regime = RegimeDetector()
        self.vwap_engine = VWAPSignalEngine()

        # Simulator state
        self.positions: dict[str, Position] = {}  # keyed by strategy
        self.pending_ict: Optional[PendingLimit] = None
        self.pending_vwap: Optional[PendingLimit] = None
        self.was_stopped_out = False
        self.active_setup_id: Optional[str] = None

        self.trades: list[dict] = []
        self.equity_curve: list[tuple] = []
        self._last_15m: Optional[pd.Timestamp] = None
        self._last_4h: Optional[pd.Timestamp] = None

        # Order lifecycle counters — live re-fires signals for a persisting
        # setup and each placement burns the shared daily limit even when the
        # order never fills, so churn matters to the results.
        self.counters = {
            "ict_orders_placed": 0,
            "ict_orders_replaced": 0,
            "ict_orders_expired": 0,
            "ict_orders_filled": 0,
            "vwap_orders_placed": 0,
            "vwap_orders_expired": 0,
            "vwap_orders_filled": 0,
        }
        self.vwap_ttl_min = 15  # reversion window: 3 five-minute candles

        # Precomputed candle boundary arrays for fast windowing
        self._starts = {}
        self._closes = {}
        for tf, df in frames.items():
            starts = df.index.tz_convert("UTC").as_unit("ns").asi8
            self._starts[tf] = starts
            self._closes[tf] = starts + TF_SECONDS[tf] * 1_000_000_000

        # Weekend NWOG anchors precomputed from the 1m stream
        self._nwogs = self._precompute_nwogs(frames["1m"])
        self._nwog_i = 0

    # ------------------------------------------------------------------ setup

    @staticmethod
    def _precompute_nwogs(df_1m: pd.DataFrame) -> list[tuple]:
        """[(sunday_open_ts, friday_close_px, sunday_open_px)] for each weekend."""
        idx = df_1m.index
        fri_mask = (idx.dayofweek == 4) & (idx.hour == 16) & (idx.minute == 59)
        sun_mask = (idx.dayofweek == 6) & (idx.hour == 18) & (idx.minute == 0)
        fridays = df_1m[fri_mask]
        sundays = df_1m[sun_mask]
        out = []
        for sun_ts, sun_row in sundays.iterrows():
            prior = fridays[fridays.index < sun_ts]
            if prior.empty:
                continue
            out.append((sun_ts, float(prior["close"].iloc[-1]), float(sun_row["open"])))
        return out

    def _window(self, tf: str, now_ns: int) -> pd.DataFrame:
        """Closed candles of `tf` up to `now`, trimmed to the live fetch limit."""
        n = int(np.searchsorted(self._closes[tf], now_ns, side="right"))
        lo = max(0, n - WINDOW_LIMITS[tf])
        return self.frames[tf].iloc[lo:n]

    # ------------------------------------------------------------ trade close

    def _fee(self, price: float, qty: float, kind: str) -> float:
        rate = config.MAKER_FEE_PCT if kind == "maker" else config.TAKER_FEE_PCT
        return price * qty * rate / 100.0

    def _close_position(self, pos: Position, exit_price: float, exit_kind: str,
                        reason: str, ts: pd.Timestamp):
        exit_fee = self._fee(exit_price, pos.qty, exit_kind)
        sign = 1.0 if pos.direction == "LONG" else -1.0
        gross = sign * (exit_price - pos.entry_price) * pos.qty
        net = gross - pos.entry_fee - exit_fee
        self.balance += net

        risk_amt = abs(pos.entry_price - pos.meta.get("orig_sl", pos.stop_loss)) * pos.qty
        self.trades.append({
            "strategy": pos.strategy,
            "direction": pos.direction,
            "opened_at": pos.opened_at,
            "closed_at": ts,
            "entry": pos.entry_price,
            "exit": exit_price,
            "qty": pos.qty,
            "reason": reason,
            "gross_pnl": gross,
            "fees": pos.entry_fee + exit_fee,
            "net_pnl": net,
            "r_multiple": (net / risk_amt) if risk_amt > 0 else 0.0,
            "balance_after": self.balance,
            **{k: v for k, v in pos.meta.items() if k in ("tier", "fib_zone", "band", "mode", "rr")},
        })
        del self.positions[pos.strategy]

        if pos.strategy == "ICT":
            if reason == "SL":
                self.was_stopped_out = True  # arm re-entry, mirror main.py
            else:
                self.was_stopped_out = False
                self.active_setup_id = None

    # -------------------------------------------------------- candle handling

    def _process_candle(self, ts: pd.Timestamp, o: float, h: float, l: float, c: float):
        """Fills, stops, targets and breakeven for one 1m candle."""
        slip = config.SLIPPAGE_PCT / 100.0

        # 1. Pending VWAP limit order (resting at the confirmation-candle close)
        if self.pending_vwap is not None:
            if ts >= self.pending_vwap.expires_at:
                self.pending_vwap = None
                self.counters["vwap_orders_expired"] += 1
            else:
                sig = self.pending_vwap.signal
                touched = (l <= sig.entry_price) if sig.direction == "LONG" else (h >= sig.entry_price)
                if touched and "VWAP" not in self.positions:
                    fill = min(sig.entry_price, o) if sig.direction == "LONG" else max(sig.entry_price, o)
                    qty = self.pending_vwap.qty
                    be_target = fill if not self.legacy_breakeven else sig.breakeven_price
                    self.positions["VWAP"] = Position(
                        strategy="VWAP", direction=sig.direction, qty=qty,
                        entry_price=fill, stop_loss=sig.stop_loss,
                        take_profit=sig.take_profit,
                        entry_fee=self._fee(fill, qty, "maker"),
                        opened_at=ts, entry_kind="maker",
                        meta={"band": sig.band, "tier": sig.tier, "mode": "vwap",
                              "rr": sig.risk_reward, "orig_sl": sig.stop_loss},
                        be_trigger=sig.breakeven_price, be_target=be_target,
                        fill_candle=ts,
                    )
                    self.pending_vwap = None
                    self.counters["vwap_orders_filled"] += 1

        # 2. Pending ICT limit order
        if self.pending_ict is not None:
            if ts >= self.pending_ict.expires_at:
                self.pending_ict = None
                self.counters["ict_orders_expired"] += 1
            else:
                sig = self.pending_ict.signal
                touched = (l <= sig.entry_price) if sig.direction == "LONG" else (h >= sig.entry_price)
                if touched and "ICT" not in self.positions:
                    # Limit fills at limit or better (gap through the level)
                    fill = min(sig.entry_price, o) if sig.direction == "LONG" else max(sig.entry_price, o)
                    qty = self.pending_ict.qty
                    self.positions["ICT"] = Position(
                        strategy="ICT", direction=sig.direction, qty=qty,
                        entry_price=fill, stop_loss=sig.stop_loss,
                        take_profit=sig.take_profit,
                        entry_fee=self._fee(fill, qty, "maker"),
                        opened_at=ts, entry_kind="maker",
                        meta={"tier": sig.tier, "fib_zone": sig.fib_zone,
                              "mode": sig.mode, "rr": sig.risk_reward,
                              "orig_sl": sig.stop_loss},
                        fill_candle=ts,
                    )
                    self.pending_ict = None
                    self.counters["ict_orders_filled"] += 1

        # 3. SL / TP / breakeven per open position
        for strategy in list(self.positions.keys()):
            pos = self.positions[strategy]
            same_candle_as_fill = pos.fill_candle == ts

            if pos.direction == "LONG":
                sl_hit = l <= pos.stop_loss
                tp_hit = h >= pos.take_profit and not same_candle_as_fill
                be_touch = pos.be_trigger is not None and h >= pos.be_trigger
            else:
                sl_hit = h >= pos.stop_loss
                tp_hit = l <= pos.take_profit and not same_candle_as_fill
                be_touch = pos.be_trigger is not None and l <= pos.be_trigger

            if sl_hit:  # conservative: stop beats target inside one candle
                exit_px = (
                    pos.stop_loss * (1 - slip) if pos.direction == "LONG"
                    else pos.stop_loss * (1 + slip)
                )
                self._close_position(pos, exit_px, "taker", "SL", ts)
                continue
            if tp_hit:
                # TP is a resting limit at the target -> maker fee
                self._close_position(pos, pos.take_profit, "maker", "TP", ts)
                continue

            # Breakeven applies from the NEXT candle (intra-candle sequence unknowable)
            if be_touch and not pos.be_done:
                if pos.direction == "LONG":
                    pos.stop_loss = max(pos.stop_loss, pos.be_target)
                else:
                    pos.stop_loss = min(pos.stop_loss, pos.be_target)
                pos.be_done = True

    # ------------------------------------------------------------ strategy tick

    def _tick(self, now: pd.Timestamp, now_ns: int, current_price: float):
        """Mirror of main.TradingBot._tick decision flow at a candle close."""
        df_1m = self._window("1m", now_ns)
        df_5m = self._window("5m", now_ns)
        df_15m = self._window("15m", now_ns)
        df_1h = self._window("1h", now_ns)
        df_4h = self._window("4h", now_ns)

        if len(df_1h) < 12 or len(df_4h) < 6 or len(df_5m) < 30:
            return

        # HTF sus-candle scans on new 15m/4h closes (mirrors _check_htf_updates)
        if len(df_15m) and df_15m.index[-1] != self._last_15m:
            self._last_15m = df_15m.index[-1]
            self.signal_engine.key_levels.scan_sus_candles(df_15m, "15m")
        if len(df_4h) and df_4h.index[-1] != self._last_4h:
            self._last_4h = df_4h.index[-1]
            self.signal_engine.key_levels.scan_sus_candles(df_4h, "4h")

        # NWOG rollover (mirrors _update_nwog, but per-weekend instead of boot-only)
        while self._nwog_i < len(self._nwogs) and self._nwogs[self._nwog_i][0] <= now:
            _, fri_close, sun_open = self._nwogs[self._nwog_i]
            self.signal_engine.key_levels.nwog = NWOG(
                anchor_a=fri_close, anchor_b=sun_open,
                ce=(fri_close + sun_open) / 2,
            )
            self._nwog_i += 1

        # ATR auto mode switching (always runs, like main.py)
        recommended = self.atr_switcher.evaluate(df_5m)
        if recommended != config.ENTRY_MODE:
            config.ENTRY_MODE = recommended

        can_trade, _ = self.risk.can_trade(now)

        # ── ICT ─────────────────────────────────────────────────────────
        if can_trade and "ICT" not in self.positions:
            signal = self.signal_engine.evaluate(
                df_1m=df_1m, df_5m=df_5m, df_15m=df_15m,
                df_1h=df_1h, df_4h=df_4h,
                current_price=current_price, now=now,
            )
            if signal is not None:
                if self.was_stopped_out and self.active_setup_id == signal.setup_id:
                    can_re, _t = self.risk.can_re_enter(signal.setup_id)
                    if not can_re:
                        signal = None
            if signal is not None:
                qty = self.risk.calculate_position_size(
                    self.balance, signal.entry_price, signal.stop_loss,
                )
                if qty > 0:
                    # Replaces any unfilled prior order (live would stack them)
                    if self.pending_ict is not None:
                        self.counters["ict_orders_replaced"] += 1
                    self.counters["ict_orders_placed"] += 1
                    self.pending_ict = PendingLimit(
                        signal=signal, qty=qty, placed_at=now,
                        expires_at=now + pd.Timedelta(minutes=self.order_ttl_min),
                    )
                    self.risk.record_trade(now)
                    self.risk.record_re_entry(signal.setup_id)
                    self.active_setup_id = signal.setup_id
                    self.was_stopped_out = False
                    return  # main.py skips VWAP on the candle an ICT trade fires

        # ── VWAP ────────────────────────────────────────────────────────
        # Breakeven is handled candle-by-candle in _process_candle, so with a
        # position open (or trading blocked) there is nothing to compute.
        if not can_trade or "VWAP" in self.positions or self.pending_vwap is not None:
            return
        vwap_data = self.vwap_calc.compute(df_5m, now)
        if vwap_data is None:
            return
        regime = self.regime.get_regime(vwap_data, df_5m)
        vwap_signal = self.vwap_engine.evaluate(df_5m, vwap_data, regime, now)
        if vwap_signal is None:
            return
        qty = self.risk.calculate_position_size(
            self.balance, vwap_signal.entry_price, vwap_signal.stop_loss,
        )
        if qty <= 0:
            return
        self.pending_vwap = PendingLimit(
            signal=vwap_signal, qty=qty, placed_at=now,
            expires_at=now + pd.Timedelta(minutes=self.vwap_ttl_min),
        )
        self.counters["vwap_orders_placed"] += 1
        self.risk.record_trade(now)
        self.vwap_engine.record_trade(now)

    # ------------------------------------------------------------------- run

    def run(self, progress_every: int = 20000) -> dict:
        df_1m = self.frames["1m"]
        idx = df_1m.index
        opens = df_1m["open"].to_numpy()
        highs = df_1m["high"].to_numpy()
        lows = df_1m["low"].to_numpy()
        closes = df_1m["close"].to_numpy()
        starts_ns = self._starts["1m"]

        n = len(df_1m)
        for i in range(n):
            ts = idx[i]
            self._process_candle(ts, opens[i], highs[i], lows[i], closes[i])

            now = ts + pd.Timedelta(minutes=1)  # the moment this candle closed
            now_ns = starts_ns[i] + 60 * 1_000_000_000

            # Tick cadence mirrors main.py's sleep interval per entry mode
            if config.ENTRY_MODE == "5m":
                tick_due = (now.minute % 5) == 0
            else:  # "1m" and "hybrid" tick every minute
                tick_due = True
            if tick_due:
                self._tick(now, now_ns, closes[i])

            # Equity mark every 5 minutes
            if now.minute % 5 == 0:
                unrealized = sum(
                    (1.0 if p.direction == "LONG" else -1.0)
                    * (closes[i] - p.entry_price) * p.qty
                    for p in self.positions.values()
                )
                self.equity_curve.append((now, self.balance + unrealized))

            if progress_every and i % progress_every == 0 and i > 0:
                logger.info(
                    "[%s] %s | %d/%d | balance %.2f | trades %d",
                    self.name, ts, i, n, self.balance, len(self.trades),
                )

        # Force-close anything left open at the final close (mark-to-market)
        for strategy in list(self.positions.keys()):
            pos = self.positions[strategy]
            self._close_position(pos, closes[-1], "taker", "EOD", idx[-1])

        return self.summary()

    # --------------------------------------------------------------- reporting

    def summary(self) -> dict:
        out = {"name": self.name, "start_balance": self.start_balance,
               "end_balance": round(self.balance, 2),
               "return_pct": round((self.balance / self.start_balance - 1) * 100, 2),
               "max_drawdown_pct": self._max_drawdown(),
               "orders": dict(self.counters),
               "strategies": {}}
        df = pd.DataFrame(self.trades)
        for strat in ("ICT", "VWAP"):
            sub = df[df["strategy"] == strat] if not df.empty else df
            if sub.empty:
                out["strategies"][strat] = {"trades": 0}
                continue
            wins = sub[sub["net_pnl"] > 0]
            losses = sub[sub["net_pnl"] <= 0]
            gross_win = wins["net_pnl"].sum()
            gross_loss = -losses["net_pnl"].sum()
            out["strategies"][strat] = {
                "trades": int(len(sub)),
                "wins": int(len(wins)),
                "win_rate_pct": round(100 * len(wins) / len(sub), 1),
                "net_pnl": round(sub["net_pnl"].sum(), 2),
                "gross_pnl": round(sub["gross_pnl"].sum(), 2),
                "fees": round(sub["fees"].sum(), 2),
                "avg_r": round(sub["r_multiple"].mean(), 3),
                "profit_factor": round(gross_win / gross_loss, 2) if gross_loss > 0 else float("inf"),
                "by_reason": sub["reason"].value_counts().to_dict(),
            }
        return out

    def _max_drawdown(self) -> float:
        if not self.equity_curve:
            return 0.0
        eq = pd.Series([e for _, e in self.equity_curve])
        dd = (eq / eq.cummax() - 1).min()
        return round(abs(dd) * 100, 2)
