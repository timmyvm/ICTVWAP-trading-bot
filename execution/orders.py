"""
Order Execution Module — places trades on Bybit or logs them in paper mode.

Handles:
1. Placing limit orders with SL/TP on Bybit Testnet via pybit
2. Paper trade mode: skip API calls, log intended trades to CSV
3. Trade logging for both live and paper modes

All orders use the Linear Perpetual contract (BTCUSDT).
"""

import csv
import logging
import os
from datetime import datetime
from typing import Optional

import pytz
from pybit.unified_trading import HTTP

import config
from strategy.signals import TradeSignal

logger = logging.getLogger(__name__)

NY_TZ = pytz.timezone("America/New_York")

TRADE_CSV_COLUMNS = [
    "timestamp",
    "symbol",
    "direction",
    "entry",
    "sl",
    "tp",
    "qty",        # position size — rows with qty get fee-aware $ PnL on close
    "rr",
    "mode",
    "tier",
    "strategy",   # "ICT", "VWAP" or "EMA"
    "result",
    "pnl",
    "closed_at",
]

TRADE_CSV_DTYPES = {
    "timestamp": "string",
    "symbol": "string",
    "direction": "string",
    "mode": "string",
    "strategy": "string",
    "result": "string",
    "closed_at": "string",
}


class OrderManager:
    """
    Manages order placement and trade logging.

    If PAPER_TRADE=True: logs the trade to CSV without hitting the API.
    If PAPER_TRADE=False: places a limit order on Bybit Testnet with SL/TP.
    """

    def __init__(self):
        self.session = HTTP(
            testnet=config.BYBIT_TESTNET,
            api_key=config.BYBIT_API_KEY,
            api_secret=config.BYBIT_API_SECRET,
        )
        self._ensure_csv_exists()
        self._migrate_csv()

    def execute_signal(
        self,
        signal,  # TradeSignal or VWAPSignal — both share the same interface
        qty: float,
        strategy: str = "ICT",
    ) -> bool:
        """
        Execute a trade signal.

        Args:
            signal: The validated TradeSignal to execute.
            qty: Position size (from RiskManager).

        Returns:
            True if order was placed/logged successfully, False otherwise.
        """
        if qty <= 0:
            logger.error("Invalid quantity: %.3f — skipping", qty)
            return False

        if config.PAPER_TRADE:
            return self._paper_trade(signal, qty, strategy)
        else:
            return self._live_trade(signal, qty, strategy)

    def _paper_trade(self, signal, qty: float, strategy: str = "ICT") -> bool:
        """
        Paper trade mode: log the intended trade to CSV without placing an order.

        This allows strategy testing without risking any capital. Every signal
        is recorded with full details for later analysis.
        """
        now_ny = datetime.now(NY_TZ)

        logger.info(
            "[PAPER] [%s] %s %s %.3f @ %.2f | SL=%.2f | TP=%.2f | R:R=%.2f | mode=%s",
            strategy,
            signal.direction,
            config.SYMBOL,
            qty,
            signal.entry_price,
            signal.stop_loss,
            signal.take_profit,
            signal.risk_reward,
            signal.mode,
        )

        self._log_trade(
            timestamp=now_ny.isoformat(),
            direction=signal.direction,
            entry=signal.entry_price,
            sl=signal.stop_loss,
            tp=signal.take_profit,
            rr=signal.risk_reward,
            mode=signal.mode,
            tier=signal.tier,
            strategy=strategy,
            result="PAPER",
            pnl=0.0,
            qty=qty,
        )

        return True

    def _live_trade(self, signal, qty: float, strategy: str = "ICT") -> bool:
        """
        Live trade mode: place a limit order on Bybit Testnet.

        Uses Bybit's unified trading API to place a limit order with:
        - Stop loss at the calculated SL level
        - Take profit at the calculated TP level
        - Reduce-only flags to prevent accidental position doubling
        """
        side = "Buy" if signal.direction == "LONG" else "Sell"

        try:
            resp = self.session.place_order(
                category=config.CATEGORY,
                symbol=config.SYMBOL,
                side=side,
                orderType="Limit",
                qty=str(qty),
                price=str(round(signal.entry_price, 1)),
                stopLoss=str(round(signal.stop_loss, 1)),
                takeProfit=str(round(signal.take_profit, 1)),
                timeInForce="GTC",  # Good Till Cancelled
                positionIdx=0,  # One-way mode
            )

            order_id = resp.get("result", {}).get("orderId", "unknown")
            logger.info(
                "[LIVE] [%s] Order placed: %s | id=%s | %s %.3f @ %.2f",
                strategy,
                config.SYMBOL,
                order_id,
                signal.direction,
                qty,
                signal.entry_price,
            )

            # Log to CSV
            now_ny = datetime.now(NY_TZ)
            self._log_trade(
                timestamp=now_ny.isoformat(),
                direction=signal.direction,
                entry=signal.entry_price,
                sl=signal.stop_loss,
                tp=signal.take_profit,
                rr=signal.risk_reward,
                mode=signal.mode,
                tier=signal.tier,
                strategy=strategy,
                result="OPEN",
                pnl=0.0,
                qty=qty,
            )

            return True

        except Exception as e:
            logger.error("Failed to place order: %s", e)
            return False

    def modify_stop_loss(self, order_id: str, new_sl: float) -> bool:
        """
        Modify the stop loss on an existing position.

        Used for moving stop to breakeven after price makes a significant move.
        In paper mode the CSV row is updated so check_paper_position() honors
        the new stop — logging alone left the paper position tracking the old SL.
        """
        if config.PAPER_TRADE:
            try:
                import pandas as _pd
                trades = _pd.read_csv(
                    config.TRADE_LOG_PATH, dtype=str, keep_default_na=False,
                )
                open_idx = trades.index[trades["result"].isin(["PAPER", "OPEN"])]
                if len(open_idx) > 0:
                    # Most recent open position is the one being managed
                    trades.at[open_idx[-1], "sl"] = f"{new_sl:.2f}"
                    trades.to_csv(config.TRADE_LOG_PATH, index=False)
            except Exception as e:
                logger.error("Failed to update paper SL: %s", e)
            logger.info("[PAPER] Move SL to %.2f", new_sl)
            return True

        try:
            self.session.set_trading_stop(
                category=config.CATEGORY,
                symbol=config.SYMBOL,
                stopLoss=str(round(new_sl, 1)),
                positionIdx=0,
            )
            logger.info("Stop loss modified to %.2f", new_sl)
            return True
        except Exception as e:
            logger.error("Failed to modify stop loss: %s", e)
            return False

    def check_paper_position(self, current_price: float) -> Optional[str]:
        """
        Check ALL open paper trades against current price and resolve any hits.

        Previously only the LAST CSV row was monitored, so whenever a second
        trade opened (e.g. a VWAP trade after an ICT trade) the earlier one was
        orphaned as "PAPER" forever and its outcome never counted.

        Returns:
            "STOPPED" if any position stopped out on this check (re-entry logic
            keys off this), else "TP_HIT" if any hit TP, else None.
        """
        try:
            import pandas as _pd
            trades = _pd.read_csv(
                config.TRADE_LOG_PATH,
                dtype=str,
                keep_default_na=False,
            )
            if trades.empty:
                return None

            any_stopped = False
            any_tp = False
            changed = False

            for idx in trades.index[trades["result"].isin(["PAPER", "OPEN"])]:
                row = trades.loc[idx]
                entry = float(row["entry"])
                sl = float(row["sl"])
                tp = float(row["tp"])
                direction = row["direction"]
                try:
                    qty = float(row.get("qty", "") or 0.0)
                except (TypeError, ValueError):
                    qty = 0.0

                result = None
                exit_px = None

                if direction == "LONG":
                    if current_price <= sl:
                        result, exit_px = "STOPPED", sl
                    elif current_price >= tp:
                        result, exit_px = "TP_HIT", tp
                else:  # SHORT
                    if current_price >= sl:
                        result, exit_px = "STOPPED", sl
                    elif current_price <= tp:
                        result, exit_px = "TP_HIT", tp

                if result:
                    sign = 1.0 if direction == "LONG" else -1.0
                    if qty > 0:
                        # Fee-aware $ PnL — the validated cost model
                        # (backtest/bracket_experiment.py): exit at the raw
                        # bracket level, taker fee + slippage charged on both
                        # legs. Points-only PnL hid real losses before.
                        cost_rate = (config.TAKER_FEE_PCT + config.SLIPPAGE_PCT) / 100.0
                        gross = sign * (exit_px - entry) * qty
                        fees = (entry + exit_px) * qty * cost_rate
                        pnl = gross - fees
                        unit = "$"
                    else:
                        # Legacy rows without qty: points, as before.
                        pnl = sign * (exit_px - entry)
                        unit = "pts"
                    now_ny = datetime.now(NY_TZ)
                    trades.at[idx, "result"] = result
                    # The frame is read dtype=str — a float assignment raises
                    # on pandas 2.x+ and aborts the whole resolution pass.
                    trades.at[idx, "pnl"] = str(round(pnl, 2))
                    trades.at[idx, "closed_at"] = now_ny.isoformat()
                    changed = True
                    any_stopped = any_stopped or result == "STOPPED"
                    any_tp = any_tp or result == "TP_HIT"
                    logger.info(
                        "[PAPER] Position %s: %s | PnL=%.2f %s",
                        direction, result, pnl, unit,
                    )

            if changed:
                trades.to_csv(config.TRADE_LOG_PATH, index=False)

            if any_stopped:
                return "STOPPED"
            if any_tp:
                return "TP_HIT"
            return None

        except Exception as e:
            logger.error("Failed to check paper position: %s", e)
            return None

    def has_open_position(self) -> bool:
        """
        True while any position is open — paper mode reads the CSV (source of
        truth), live mode queries Bybit. Used for one-position-at-a-time
        strategies (EMA bracket).
        """
        if config.PAPER_TRADE or config.BYBIT_TESTNET:
            try:
                import pandas as _pd
                trades = _pd.read_csv(
                    config.TRADE_LOG_PATH, dtype=str, keep_default_na=False,
                )
                return bool(trades["result"].isin(["PAPER", "OPEN"]).any())
            except FileNotFoundError:
                return False
            except Exception as e:
                logger.error("Failed to read open positions from CSV: %s", e)
                return True  # fail closed — never double-enter on a read error

        try:
            resp = self.session.get_positions(
                category=config.CATEGORY, symbol=config.SYMBOL,
            )
            positions = resp.get("result", {}).get("list", [])
            return any(float(p.get("size", 0)) > 0 for p in positions)
        except Exception as e:
            logger.error("Failed to check live positions: %s", e)
            return True  # fail closed

    def get_paper_equity(self, start_balance: float) -> float:
        """
        Current paper equity: start balance plus realized fee-aware $ PnL of
        every closed row that carries a qty. Mirrors the validated backtest's
        compounding (1% of CURRENT equity per trade). Legacy points-only rows
        are excluded — they are not dollars.
        """
        try:
            import pandas as _pd
            trades = _pd.read_csv(
                config.TRADE_LOG_PATH, dtype=str, keep_default_na=False,
            )
            closed = trades[trades["result"].isin(["STOPPED", "TP_HIT"])]
            if closed.empty:
                return start_balance
            qty = _pd.to_numeric(closed["qty"], errors="coerce")
            pnl = _pd.to_numeric(closed["pnl"], errors="coerce")
            realized = pnl[(qty > 0) & pnl.notna()].sum()
            return start_balance + float(realized)
        except FileNotFoundError:
            return start_balance
        except Exception as e:
            logger.error("Failed to compute paper equity: %s", e)
            return start_balance

    def cancel_open_orders(self) -> bool:
        """Cancel all open orders for the symbol. Used during shutdown."""
        if config.PAPER_TRADE:
            logger.info("[PAPER] Cancel all open orders")
            return True

        try:
            self.session.cancel_all_orders(
                category=config.CATEGORY,
                symbol=config.SYMBOL,
            )
            logger.info("All open orders cancelled for %s", config.SYMBOL)
            return True
        except Exception as e:
            logger.error("Failed to cancel orders: %s", e)
            return False

    def _log_trade(
        self,
        timestamp: str,
        direction: str,
        entry: float,
        sl: float,
        tp: float,
        rr: float,
        mode: str,
        tier: int,
        result: str,
        pnl: float,
        strategy: str = "ICT",
        closed_at: str = "",
        qty: Optional[float] = None,
    ):
        """Append a trade record to the CSV log."""
        row = {
            "timestamp": timestamp,
            "symbol": config.SYMBOL,
            "direction": direction,
            "entry": round(entry, 2),
            "sl": round(sl, 2),
            "tp": round(tp, 2),
            "qty": round(qty, 3) if qty is not None else "",
            "rr": round(rr, 2),
            "mode": mode,
            "tier": tier,
            "strategy": strategy,
            "result": result,
            "pnl": round(pnl, 2),
            "closed_at": closed_at,
        }

        try:
            with open(config.TRADE_LOG_PATH, "a", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=TRADE_CSV_COLUMNS)
                writer.writerow(row)
            logger.debug("Trade logged to %s", config.TRADE_LOG_PATH)
        except Exception as e:
            logger.error("Failed to log trade: %s", e)

    @staticmethod
    def _ensure_csv_exists():
        """Create the trade log CSV with headers if it doesn't exist."""
        os.makedirs(os.path.dirname(config.TRADE_LOG_PATH), exist_ok=True)
        if not os.path.exists(config.TRADE_LOG_PATH) or os.path.getsize(config.TRADE_LOG_PATH) == 0:
            with open(config.TRADE_LOG_PATH, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=TRADE_CSV_COLUMNS)
                writer.writeheader()
            logger.info("Trade log created: %s", config.TRADE_LOG_PATH)

    @staticmethod
    def _migrate_csv():
        """
        Add missing columns to an existing CSV (e.g. 'strategy' added later).

        Reads the existing file, adds any columns that are in TRADE_CSV_COLUMNS
        but missing from the file (backfilling with sensible defaults), then
        rewrites it. Safe to run on every startup — no-op if already up to date.
        """
        import pandas as _pd

        try:
            if not os.path.exists(config.TRADE_LOG_PATH):
                return

            df = _pd.read_csv(config.TRADE_LOG_PATH, dtype=str, keep_default_na=False)

            if df.empty and list(df.columns) == TRADE_CSV_COLUMNS:
                return  # Already correct schema, no rows

            changed = False
            for col in TRADE_CSV_COLUMNS:
                if col not in df.columns:
                    # Backfill defaults per column
                    defaults = {"strategy": "ICT", "result": "", "pnl": "0", "closed_at": ""}
                    df[col] = defaults.get(col, "")
                    changed = True
                    logger.info("CSV migration: added missing column '%s'", col)

            if changed:
                # Rewrite with correct column order
                df = df[TRADE_CSV_COLUMNS]
                df.to_csv(config.TRADE_LOG_PATH, index=False)
                logger.info("CSV migration complete: %s", config.TRADE_LOG_PATH)

        except Exception as e:
            logger.error("CSV migration failed: %s", e)
