"""
Risk Management Module — position sizing, trade limits, and re-entry logic.

This module enforces the risk rules that keep the account alive:
1. Never risk more than RISK_PER_TRADE_PCT of account per trade
2. Cap daily and weekly trade counts
3. Allow re-entries at deeper fib levels if stopped out
4. Skip trades during high-impact news
5. Move stop to breakeven after significant move in our favor
"""

import logging
from datetime import datetime, date, timedelta
from typing import Optional

import pytz

import config

logger = logging.getLogger(__name__)

NY_TZ = pytz.timezone("America/New_York")


class RiskManager:
    """
    Manages position sizing, trade limits, and re-entry logic.
    """

    def __init__(self):
        # Track trades per day and week for limit enforcement
        self.daily_trades: dict[date, int] = {}
        self.weekly_trades: dict[int, int] = {}  # keyed by ISO week number

        # Re-entry tracking per setup
        self.re_entry_count: int = 0
        self.last_setup_id: Optional[str] = None

    def calculate_position_size(
        self,
        account_balance: float,
        entry_price: float,
        stop_loss: float,
    ) -> float:
        """
        Calculate position size based on risk percentage.

        Formula:
          risk_amount = account_balance * (RISK_PER_TRADE_PCT / 100)
          risk_per_unit = |entry_price - stop_loss|
          position_size = risk_amount / risk_per_unit

        This ensures we never lose more than RISK_PER_TRADE_PCT of our account
        on any single trade, regardless of where the stop is.
        """
        risk_amount = account_balance * (config.RISK_PER_TRADE_PCT / 100)
        risk_per_unit = abs(entry_price - stop_loss)

        if risk_per_unit == 0:
            logger.error("Risk per unit is zero — cannot calculate position size")
            return 0.0

        qty = risk_amount / risk_per_unit

        # Round down to 3 decimal places (Bybit BTCUSDT min qty)
        qty = round(qty, 3)

        logger.info(
            "Position size: balance=%.2f, risk=%.2f%%, risk_amt=%.2f, "
            "risk_per_unit=%.2f, qty=%.3f",
            account_balance,
            config.RISK_PER_TRADE_PCT,
            risk_amount,
            risk_per_unit,
            qty,
        )
        return qty

    def can_trade(self) -> tuple[bool, str]:
        """
        Check if we're allowed to take a new trade.

        Checks:
        1. Daily trade limit
        2. Weekly trade limit
        3. News blackout windows (NFP, CPI)

        Returns:
            (allowed, reason) — reason is empty if allowed.
        """
        now_ny = datetime.now(NY_TZ)
        today = now_ny.date()
        iso = today.isocalendar()
        week_key = (iso[0], iso[1])  # (year, week) — avoids year-boundary collisions

        # Daily limit
        daily_count = self.daily_trades.get(today, 0)
        if daily_count >= config.MAX_DAILY_TRADES:
            return False, f"Daily limit reached ({daily_count}/{config.MAX_DAILY_TRADES})"

        # Weekly limit
        weekly_count = self.weekly_trades.get(week_key, 0)
        if weekly_count >= config.MAX_WEEKLY_TRADES:
            return False, f"Weekly limit reached ({weekly_count}/{config.MAX_WEEKLY_TRADES})"

        # News blackout check
        if self._is_news_blackout(now_ny):
            return False, "News blackout window — skipping trade"

        return True, ""

    def record_trade(self):
        """Record that a trade was taken (increment daily/weekly counters)."""
        now_ny = datetime.now(NY_TZ)
        today = now_ny.date()
        iso = today.isocalendar()
        week_key = (iso[0], iso[1])  # (year, week) — avoids year-boundary collisions

        self.daily_trades[today] = self.daily_trades.get(today, 0) + 1
        self.weekly_trades[week_key] = self.weekly_trades.get(week_key, 0) + 1

        logger.info(
            "Trade recorded: daily=%d/%d, weekly=%d/%d",
            self.daily_trades[today],
            config.MAX_DAILY_TRADES,
            self.weekly_trades[week_key],
            config.MAX_WEEKLY_TRADES,
        )

    def can_re_enter(self, setup_id: str) -> tuple[bool, str]:
        """
        Check if re-entry is allowed after a stop-out.

        ICT Rule: if stopped out, we can try again at deeper fib levels:
        - First re-entry at 0.62 (OTE)
        - Second re-entry at 0.79 (Deep Discount)
        - Max 2 re-entries per setup

        The setup_id ties re-entries to the same trade idea (same fib leg).
        """
        if setup_id != self.last_setup_id:
            # New setup — reset counter
            self.last_setup_id = setup_id
            self.re_entry_count = 0

        if self.re_entry_count >= config.MAX_RE_ENTRIES:
            return False, f"Max re-entries reached ({self.re_entry_count}/{config.MAX_RE_ENTRIES})"

        self.re_entry_count += 1
        target = "OTE (0.62)" if self.re_entry_count == 1 else "Deep Discount (0.79)"
        logger.info("Re-entry #%d allowed — looking for RB at %s", self.re_entry_count, target)

        return True, target

    def get_re_entry_fib_level(self) -> float:
        """Return the fib level to target for the current re-entry attempt."""
        if self.re_entry_count <= 1:
            return 0.62  # OTE
        return 0.79  # Deep Discount

    def calculate_breakeven_level(
        self,
        entry_price: float,
        direction: str,
        significant_high: Optional[float] = None,
    ) -> Optional[float]:
        """
        Determine if stop should be moved to breakeven.

        ICT Rule: move stop to breakeven when price takes out a significant
        internal high (for longs) or internal low (for shorts).

        Returns the breakeven stop price if conditions are met, else None.
        """
        if significant_high is None:
            return None

        if direction == "LONG" and significant_high > entry_price:
            # Price has taken out a high above our entry — lock in breakeven
            logger.info(
                "Moving stop to breakeven: price hit %.2f above entry %.2f",
                significant_high,
                entry_price,
            )
            return entry_price + 1.0  # 1-point buffer above entry

        if direction == "SHORT" and significant_high < entry_price:
            logger.info(
                "Moving stop to breakeven: price hit %.2f below entry %.2f",
                significant_high,
                entry_price,
            )
            return entry_price - 1.0  # 1-point buffer below entry

        return None

    @staticmethod
    def _is_news_blackout(now_ny: datetime) -> bool:
        """
        Check if current time falls within a high-impact news window.

        NFP: first Friday of each month, typically 8:30 AM ET
        CPI: check against configured dates

        We skip trades in a window around these events because volatility
        becomes random and invalidates technical setups.
        """
        window = config.NEWS_BLACKOUT_WINDOW_MINUTES

        # NFP check: first Friday of the month
        first_day = now_ny.replace(day=1)
        days_until_friday = (4 - first_day.weekday()) % 7
        first_friday = first_day + timedelta(days=days_until_friday)

        if now_ny.date() == first_friday.date():
            nfp_time = now_ny.replace(hour=8, minute=30, second=0, microsecond=0)
            if abs((now_ny - nfp_time).total_seconds()) < window * 60:
                logger.warning("NFP blackout window active")
                return True

        # CPI check: against configured dates
        for event in config.NEWS_BLACKOUT_EVENTS:
            if isinstance(event, tuple) and len(event) == 2:
                event_name, dates = event
                if isinstance(dates, list):
                    for m, d in dates:
                        if now_ny.month == m and now_ny.day == d:
                            cpi_time = now_ny.replace(hour=8, minute=30, second=0, microsecond=0)
                            if abs((now_ny - cpi_time).total_seconds()) < window * 60:
                                logger.warning("%s blackout window active", event_name)
                                return True

        return False
