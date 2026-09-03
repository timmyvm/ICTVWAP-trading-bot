"""
Parity check: strategy/ema_bracket.py (live module) vs
backtest/bracket_experiment.py (the validated reference).

Replays a slice of cached BTC 1H data through the live module exactly the
way main.py drives it — expanding frames of CLOSED candles, current_price
= the next bar's open, evaluate() called only while flat — and asserts the
signal set (signal candle, direction, fill, stop, target) is IDENTICAL to
the reference simulation's entry events on the same data.

Run after ANY change to either file. Exit code 0 = parity holds.
"""

import sys

import numpy as np
import pandas as pd

sys.path.insert(0, ".")
from backtest.bracket_experiment import WARMUP, simulate  # noqa: E402
from backtest.data import load_cached_1m, resample_ohlcv  # noqa: E402
import config  # noqa: E402
from strategy.ema_bracket import EMABracketStrategy  # noqa: E402

BARS = 2400  # ~100 days of 1H — hundreds of trades, seconds of runtime


def main() -> int:
    df = resample_ohlcv(
        load_cached_1m("backtest/data_cache/local/btcusd_1m_2023_2026.csv.gz"), "1h",
    )
    seg = df.iloc[-BARS:]
    o = seg["open"].to_numpy()

    ref = simulate(seg, return_trades=True)
    entries = ref["entries"]
    trades = ref["trades"]

    # Comparison starts once the live module's history floor is met — the
    # reference warms up at 210 bars, the live module refuses below
    # EMA_BRACKET_MIN_1H for EMA fidelity on windowed live fetches.
    start = max(WARMUP, config.EMA_BRACKET_MIN_1H)
    entries = entries[entries["i"] >= start].reset_index(drop=True)

    # Occupied bars (evaluate is never called in-position): strictly after
    # the entry bar, strictly before the exit bar — exits resolve before the
    # entry step, and the final entry may never resolve.
    occupied = np.zeros(len(seg), dtype=bool)
    exit_i = trades["i"].tolist()
    all_entry_i = ref["entries"]["i"].tolist()
    for k, e_i in enumerate(all_entry_i):
        x_i = exit_i[k] if k < len(exit_i) else len(seg)
        occupied[e_i + 1: x_i] = True

    strat = EMABracketStrategy()
    live = []
    for i in range(start, len(seg)):
        if occupied[i]:
            continue
        sig = strat.evaluate(seg.iloc[:i], current_price=float(o[i]))
        if sig is not None:
            live.append({"i": i, "signal_ts": pd.Timestamp(sig.setup_id),
                         "dir": sig.direction, "entry": sig.entry_price,
                         "stop": sig.stop_loss, "tp": sig.take_profit})
    live_df = pd.DataFrame(live)

    print(f"reference entries (i >= {start}): {len(entries)}")
    print(f"live module signals:              {len(live_df)}")
    if len(entries) != len(live_df):
        print("PARITY FAIL: entry counts differ")
        return 1

    ok = True
    for col in ("signal_ts", "dir"):
        if not (entries[col].values == live_df[col].values).all():
            print(f"PARITY FAIL: column '{col}' differs")
            ok = False
    for col in ("entry", "stop", "tp"):
        diff = (entries[col].to_numpy() - live_df[col].to_numpy())
        mx = float(np.abs(diff).max()) if len(diff) else 0.0
        print(f"max |{col} diff| = {mx:.10f}")
        if mx > 1e-6:
            print(f"PARITY FAIL: column '{col}' differs beyond tolerance")
            ok = False

    print("PARITY PASS" if ok else "PARITY FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
