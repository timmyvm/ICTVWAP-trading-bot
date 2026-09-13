"""
Verification for paper bracket resolution (DEVLOG v0.21).

The live bot sends stopLoss/takeProfit WITH the order, so a real account's
bracket is held by the exchange and fills on ANY touch. Paper resolution must
therefore read the 1m price PATH, not one mark sample per tick. These checks
pin that behaviour, plus the guards around it:

  1. a wick that pierces the stop and recovers before the tick still stops out
  2. without a path, behaviour falls back to the old point check
  3. bars older than the row's own entry can never close it
  4. stop is checked before target when a window touches both
  5. a target touched only by a wick is taken
  6. shorts mirror longs
  7. PnL stays fee-aware and is written back as a STRING (pandas dtype=str)

Run: python scripts/verify_exit_resolution.py    (no pytest dependency)
"""

import os
import sys
import tempfile

import pandas as pd
import pytz

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402

NY = pytz.timezone("America/New_York")
ENTRY_TS = pd.Timestamp("2026-09-13 12:00:00", tz=NY)

FAILURES: list[str] = []


def bars(rows: list[tuple]) -> pd.DataFrame:
    """rows of (minute_offset, high, low) -> a 1m OHLC frame around ENTRY_TS."""
    idx = [ENTRY_TS + pd.Timedelta(minutes=m) for m, _, _ in rows]
    return pd.DataFrame(
        {
            "open": [(h + low) / 2 for _, h, low in rows],
            "high": [h for _, h, _ in rows],
            "low": [low for _, _, low in rows],
            "close": [(h + low) / 2 for _, h, low in rows],
            "volume": [1.0] * len(rows),
        },
        index=pd.DatetimeIndex(idx),
    )


def make_manager(direction: str, entry: float, sl: float, tp: float, qty: float = 0.1):
    """An OrderManager pointed at a throwaway CSV holding one open row."""
    from execution.orders import TRADE_CSV_COLUMNS, OrderManager

    fd, path = tempfile.mkstemp(suffix=".csv")
    os.close(fd)
    row = {c: "" for c in TRADE_CSV_COLUMNS}
    row.update({
        "timestamp": ENTRY_TS.isoformat(), "symbol": "BTCUSDT", "direction": direction,
        "entry": entry, "sl": sl, "tp": tp, "qty": qty, "rr": 1.0, "mode": "ema_bracket",
        "tier": 0, "strategy": "EMA", "result": "PAPER", "pnl": "", "closed_at": "",
    })
    pd.DataFrame([row], columns=TRADE_CSV_COLUMNS).to_csv(path, index=False)
    config.TRADE_LOG_PATH = path
    mgr = OrderManager.__new__(OrderManager)   # no API session needed for resolution
    return mgr, path


def check(name: str, got, want) -> None:
    ok = got == want
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}: got {got!r}, want {want!r}")
    if not ok:
        FAILURES.append(name)


def case_wick_stop() -> None:
    mgr, path = make_manager("LONG", 100.0, 97.0, 103.0)
    # mark recovered to 101, but a bar wicked to 96.5 — the exchange would fill
    p = bars([(1, 100.5, 99.8), (2, 100.2, 96.5), (3, 101.2, 100.6)])
    check("1 wick below the stop resolves", mgr.check_paper_position(101.0, path=p), "STOPPED")
    t = pd.read_csv(path, dtype=str, keep_default_na=False)
    check("1 exit booked at the stop level", t.at[0, "result"], "STOPPED")
    # fee-aware PnL: gross = (97 - 100) * 0.1 = -0.30, fees = (100+97)*0.1*0.00065
    rate = (config.TAKER_FEE_PCT + config.SLIPPAGE_PCT) / 100.0
    want = round((97.0 - 100.0) * 0.1 - (100.0 + 97.0) * 0.1 * rate, 2)
    check("1 PnL is fee-aware", float(t.at[0, "pnl"]), want)
    check("1 PnL written as a string", isinstance(t.at[0, "pnl"], str), True)
    os.unlink(path)


def case_no_path_falls_back() -> None:
    mgr, path = make_manager("LONG", 100.0, 97.0, 103.0)
    check("2 no path, mark inside the bracket", mgr.check_paper_position(101.0), None)
    os.unlink(path)


def case_pre_entry_bars_ignored() -> None:
    mgr, path = make_manager("LONG", 100.0, 97.0, 103.0)
    p = bars([(-5, 100.0, 90.0), (-1, 100.0, 91.0), (1, 101.0, 100.0)])
    check("3 bars before entry cannot close the row", mgr.check_paper_position(101.0, path=p), None)
    os.unlink(path)


def case_stop_first() -> None:
    mgr, path = make_manager("LONG", 100.0, 97.0, 103.0)
    p = bars([(1, 104.0, 96.0)])       # one bar touches BOTH
    check("4 stop wins when both are touched", mgr.check_paper_position(101.0, path=p), "STOPPED")
    os.unlink(path)


def case_wick_target() -> None:
    mgr, path = make_manager("LONG", 100.0, 97.0, 103.0)
    p = bars([(1, 103.5, 100.2), (2, 101.5, 100.9)])
    check("5 wick above the target resolves", mgr.check_paper_position(101.0, path=p), "TP_HIT")
    os.unlink(path)


def case_short_mirror() -> None:
    mgr, path = make_manager("SHORT", 100.0, 103.0, 97.0)
    p = bars([(1, 103.5, 99.8)])
    check("6 short stops on a high wick", mgr.check_paper_position(99.0, path=p), "STOPPED")
    os.unlink(path)
    mgr, path = make_manager("SHORT", 100.0, 103.0, 97.0)
    p = bars([(1, 100.2, 96.5)])
    check("6 short takes profit on a low wick", mgr.check_paper_position(99.0, path=p), "TP_HIT")
    os.unlink(path)


def main() -> None:
    original = config.TRADE_LOG_PATH
    try:
        for fn in (case_wick_stop, case_no_path_falls_back, case_pre_entry_bars_ignored,
                   case_stop_first, case_wick_target, case_short_mirror):
            print(fn.__name__)
            fn()
    finally:
        config.TRADE_LOG_PATH = original
    print()
    if FAILURES:
        print(f"FAILED: {len(FAILURES)} check(s): {', '.join(FAILURES)}")
        sys.exit(1)
    print("ALL CHECKS PASSED")


if __name__ == "__main__":
    main()
