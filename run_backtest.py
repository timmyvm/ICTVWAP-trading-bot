"""
Backtest CLI for the Powell Trades bot.

Usage:
    python run_backtest.py --days 60                  # fixed (current) code
    python run_backtest.py --days 60 --variant all    # fixed vs legacy vs no-tier
    python run_backtest.py --refresh-data 180         # re-pull from Bybit (needs API access)

Variants:
    fixed        current code with all bug fixes (defaults)
    legacy       reproduces the pre-fix behavior: legacy fib validity (kills all
                 ICT signals), no VWAP warm-up, NWOG bias override on, breakeven
                 stop parked at the ±1σ band instead of entry
    fixed_notier fixed + tier R:R floors disabled (quantifies how many trades
                 the 1:5 / 1:3 tier gates reject)

Data comes from backtest/data_cache/ (committed, Bitstamp 1m BTC/USD). On a
machine that can reach api.bybit.com (e.g. the VPS), --refresh-data replaces the
cache with real Bybit BTCUSDT perp candles.
"""

import argparse
import json
import logging
import os
import sys

import pandas as pd

import config
from backtest.data import load_frames, fetch_bybit_1m
from backtest.engine import BacktestEngine

RESULTS_DIR = os.path.join("backtest", "results")

# Config attributes each variant overrides (snapshot/restored between runs)
VARIANTS: dict[str, dict] = {
    "fixed": {},
    "legacy": {
        "FIB_VALIDITY_MODE": "legacy",
        "VWAP_MIN_SESSION_CANDLES": 0,
        "NWOG_BIAS_OVERRIDE": True,
    },
    "fixed_notier": {
        "ENFORCE_TIER_RR": False,
    },
}

CONFIG_KEYS = [
    "FIB_VALIDITY_MODE", "VWAP_MIN_SESSION_CANDLES", "NWOG_BIAS_OVERRIDE",
    "ENFORCE_TIER_RR", "ENTRY_MODE",
]


def run_variant(name: str, frames: dict, balance: float) -> dict:
    snapshot = {k: getattr(config, k) for k in CONFIG_KEYS}
    try:
        for k, v in VARIANTS[name].items():
            setattr(config, k, v)
        engine = BacktestEngine(
            frames,
            start_balance=balance,
            legacy_breakeven=(name == "legacy"),
            name=name,
        )
        summary = engine.run()

        os.makedirs(RESULTS_DIR, exist_ok=True)
        if engine.trades:
            pd.DataFrame(engine.trades).to_csv(
                os.path.join(RESULTS_DIR, f"{name}_trades.csv"), index=False,
            )
        eq = pd.DataFrame(engine.equity_curve, columns=["timestamp", "equity"])
        eq.to_csv(os.path.join(RESULTS_DIR, f"{name}_equity.csv"), index=False)
        return summary
    finally:
        for k, v in snapshot.items():
            setattr(config, k, v)


def main():
    ap = argparse.ArgumentParser(description="Backtest the Powell Trades bot")
    ap.add_argument("--days", type=int, default=60, help="trailing days to test")
    ap.add_argument("--variant", default="fixed",
                    choices=[*VARIANTS.keys(), "all"])
    ap.add_argument("--balance", type=float, default=10_000.0)
    ap.add_argument("--refresh-data", type=int, metavar="DAYS", default=None,
                    help="re-fetch N days of 1m data from Bybit into the cache")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stdout,
    )
    if not args.verbose:
        # Strategy modules log every signal decision — useful live, noise here
        for noisy in ("strategy", "execution", "backtest.data"):
            logging.getLogger(noisy).setLevel(logging.WARNING)

    if args.refresh_data:
        print(f"Fetching {args.refresh_data} days of 1m data from Bybit...")
        fetch_bybit_1m(args.refresh_data)

    frames = load_frames(days=args.days)
    span = f"{frames['1m'].index[0]} -> {frames['1m'].index[-1]}"
    print(f"Backtesting {args.days} days: {span}\n")

    names = list(VARIANTS.keys()) if args.variant == "all" else [args.variant]
    all_summaries = {}
    for name in names:
        print(f"=== variant: {name} ===")
        summary = run_variant(name, frames, args.balance)
        all_summaries[name] = summary
        print(json.dumps(summary, indent=2, default=str))
        print()

    os.makedirs(RESULTS_DIR, exist_ok=True)
    out_path = os.path.join(RESULTS_DIR, f"summary_{args.days}d.json")
    with open(out_path, "w") as f:
        json.dump({"period": span, "days": args.days, "results": all_summaries},
                  f, indent=2, default=str)
    print(f"Summaries written to {out_path}")


if __name__ == "__main__":
    main()
