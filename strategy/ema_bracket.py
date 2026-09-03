"""
v0.10c live strategy — 1H EMA-extension entries, symmetric 3xATR bracket.

The project's first VALIDATED strategy (DEVLOG v0.10c): on BTC 1H over the
unseen 2019-2022 era it scored 1,508 trades, 58.0% win, +369%, Sharpe 1.68,
maxDD 15.6%, every year positive — win rate stable at 57-58% across three
independent multi-year windows at full retail costs.

Rule (verbatim from the validated backtest, backtest/bracket_experiment.py):
  d = (close - EMA200) / ATR14 on CLOSED 1H candles.
  When flat and the last closed candle has |d| >= EMA_BRACKET_ENTRY_T,
  enter at market in the direction of the extension. Bracket both sides
  symmetrically at entry +/- EMA_BRACKET_EXIT_MULT * ATR14 (the signal
  candle's ATR). One position at a time; each closed candle sources at
  most one entry; re-entry on any later qualifying close is allowed.

backtest/parity_ema_live.py asserts this module and the backtest reference
produce identical signals on identical data — run it after ANY change here.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

import config

logger = logging.getLogger(__name__)


@dataclass
class EMABracketSignal:
    """Signal shape shared with OrderManager.execute_signal()."""
    direction: str          # "LONG" or "SHORT"
    entry_price: float      # modeled market fill: mark price +/- slippage
    stop_loss: float
    take_profit: float
    risk_reward: float = 1.0        # symmetric bracket by construction
    mode: str = "ema_bracket"
    tier: int = 0                   # tiers are an ICT concept — unused here
    setup_id: str = ""              # signal candle timestamp (ISO)
    d_value: float = field(default=0.0)   # EMA distance in ATRs at signal
    atr: float = field(default=0.0)       # signal candle's ATR14


class EMABracketStrategy:
    """
    Stateful wrapper for the live loop: tracks which closed 1H candle last
    sourced an entry so one candle never fires twice, and stays silent
    until enough history is loaded for a faithful EMA200.
    """

    def __init__(self):
        self._last_entry_candle: Optional[pd.Timestamp] = None
        self._warned_short_history = False

    def evaluate(
        self, df_1h: pd.DataFrame, current_price: float,
    ) -> Optional[EMABracketSignal]:
        """
        Evaluate the last CLOSED 1H candle (df_1h must contain closed candles
        only — the feed's drop_forming=True guarantees that).

        Returns a signal when the extension condition holds, else None.
        Call only when flat — position exclusivity lives in the main loop.
        """
        if len(df_1h) < config.EMA_BRACKET_MIN_1H:
            if not self._warned_short_history:
                logger.warning(
                    "[EMA] only %d 1H candles loaded (< %d) — standing down "
                    "until enough history for a faithful EMA%d",
                    len(df_1h), config.EMA_BRACKET_MIN_1H, config.EMA_BRACKET_SPAN,
                )
                self._warned_short_history = True
            return None

        signal_candle = df_1h.index[-1]
        if self._last_entry_candle is not None and signal_candle <= self._last_entry_candle:
            return None  # this candle already sourced an entry

        # Same math as backtest/bracket_experiment.indicators(), evaluated on
        # the last closed candle.
        close = df_1h["close"]
        ema = close.ewm(span=config.EMA_BRACKET_SPAN, adjust=False).mean()
        tr = pd.concat([
            df_1h["high"] - df_1h["low"],
            (df_1h["high"] - close.shift()).abs(),
            (df_1h["low"] - close.shift()).abs(),
        ], axis=1).max(axis=1)
        atr = tr.rolling(config.EMA_BRACKET_ATR_PERIOD).mean()

        atr_last = float(atr.iloc[-1])
        if np.isnan(atr_last) or atr_last <= 0:
            return None
        d_last = (float(close.iloc[-1]) - float(ema.iloc[-1])) / atr_last
        if abs(d_last) < config.EMA_BRACKET_ENTRY_T:
            return None

        direction = "LONG" if d_last > 0 else "SHORT"
        dr = 1 if d_last > 0 else -1
        slip = config.SLIPPAGE_PCT / 100.0
        fill = current_price * (1 + dr * slip)
        dist = config.EMA_BRACKET_EXIT_MULT * atr_last

        signal = EMABracketSignal(
            direction=direction,
            entry_price=fill,
            stop_loss=fill - dr * dist,
            take_profit=fill + dr * dist,
            setup_id=signal_candle.isoformat(),
            d_value=round(d_last, 3),
            atr=round(atr_last, 2),
        )

        # Consume the candle now: even if execution fails downstream we skip
        # rather than machine-gun retries against the same signal.
        self._last_entry_candle = signal_candle
        logger.info(
            "[EMA] signal: %s @ %.2f | d=%.2f ATRs | ATR14=%.2f | "
            "bracket +/-%.2f (SL %.2f / TP %.2f) | candle %s",
            direction, fill, d_last, atr_last, dist,
            signal.stop_loss, signal.take_profit, signal_candle,
        )
        return signal
