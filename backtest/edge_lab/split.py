"""Explore / sealed split for the strategy catalogue (docs/CATALOGUE.md section 5).

Fixed BEFORE any probe is run. Two cuts, applied together:
  * era: explore = bars on or before EXPLORE_END; sealed era = everything after;
  * coins: the universe is ranked by lifetime median daily quote volume (a liquidity rank, no
    returns), paired off 1-2, 3-4, ... and in each pair the coin with the smaller
    sha256(SALT + symbol) goes to half A, the other to half B. The ranking pairs neighbours so
    both halves hold the same mix of large and small coins; the hash makes the choice arbitrary.

The EXPLORE quadrant is (early era, half A). Phases 2 and 3 of the catalogue may read only that
quadrant. The other three quadrants are the sealed set, opened once per combination (phase 4).

Run `python3 -m backtest.edge_lab.split` to rebuild research/prereg/split_assignment.csv and print the
outcome-blind balance report (counts, liquidity ranks and listing dates only; no returns).
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Optional

import pandas as pd

SALT = "edge-split-v036"
EXPLORE_END = pd.Timestamp("2024-12-31", tz="UTC")  # last explore day, inclusive
REPO = Path(__file__).resolve().parents[2]
KLINES_1D = REPO / "backtest" / "data_cache" / "local" / "edge" / "klines_1d_um"
UNIVERSE = REPO / "backtest" / "data_cache" / "local" / "edge" / "universe_symbols.csv"
ASSIGNMENT = REPO / "research" / "prereg" / "split_assignment.csv"


def _h(symbol: str, salt: str = SALT) -> int:
    return int(hashlib.sha256((salt + symbol).encode()).hexdigest(), 16)


def pair_split(ranked_symbols: list[str], salt: str = SALT) -> dict[str, str]:
    """ranked_symbols is ordered by liquidity, most liquid first. Returns symbol -> 'A' | 'B'."""
    out: dict[str, str] = {}
    for i in range(0, len(ranked_symbols), 2):
        pair = ranked_symbols[i:i + 2]
        if len(pair) == 1:
            out[pair[0]] = "A" if _h(pair[0], salt) % 2 == 0 else "B"
            continue
        lo, hi = sorted(pair, key=lambda s: _h(s, salt))
        out[lo], out[hi] = "A", "B"
    return out


def quadrant(half: str, ts: pd.Timestamp) -> str:
    """'explore' | 'late_A' | 'early_B' | 'late_B' for a coin half and a bar timestamp."""
    ts = pd.Timestamp(ts)
    ts = ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")
    late = ts > EXPLORE_END + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
    if half == "A":
        return "late_A" if late else "explore"
    return "late_B" if late else "early_B"


def is_explore(symbol: str, ts: pd.Timestamp, assignment: dict[str, str]) -> bool:
    half: Optional[str] = assignment.get(symbol)
    if half is None:
        raise KeyError(f"{symbol} is not in the split assignment")
    return quadrant(half, ts) == "explore"


def load_assignment(path: Path = ASSIGNMENT) -> dict[str, str]:
    df = pd.read_csv(path)
    return dict(zip(df["symbol"], df["half"]))


def build() -> pd.DataFrame:
    uni = pd.read_csv(UNIVERSE)
    kept = uni[uni["excluded"].isna()]["symbol"].tolist()
    rows = []
    for s in kept:
        f = KLINES_1D / f"{s}.csv"
        if not f.exists():
            continue
        k = pd.read_csv(f, usecols=["timestamp", "quote_volume"])
        live = k[k["quote_volume"] > 0]
        if live.empty:
            continue
        t = pd.to_datetime(live["timestamp"], unit="s", utc=True)
        rows.append(dict(symbol=s, median_quote_volume=float(live["quote_volume"].median()),
                         first_day=t.min().date().isoformat(), last_day=t.max().date().isoformat(),
                         live_days=int(len(live)),
                         early_days=int((t <= EXPLORE_END).sum()), late_days=int((t > EXPLORE_END).sum())))
    df = pd.DataFrame(rows).sort_values(["median_quote_volume", "symbol"], ascending=[False, True]).reset_index(drop=True)
    df["liquidity_rank"] = df.index + 1
    half = pair_split(df["symbol"].tolist())
    df["half"] = df["symbol"].map(half)
    return df[["symbol", "half", "liquidity_rank", "median_quote_volume", "first_day", "last_day",
               "live_days", "early_days", "late_days"]]


def balance_report(df: pd.DataFrame) -> str:
    a, b = df[df.half == "A"], df[df.half == "B"]
    lines = [f"coins: A={len(a)}  B={len(b)}",
             f"median liquidity rank: A={a.liquidity_rank.median():.0f}  B={b.liquidity_rank.median():.0f}",
             f"median first listing: A={pd.to_datetime(a.first_day).median().date()}  B={pd.to_datetime(b.first_day).median().date()}",
             f"top-20 coins: A={int((a.liquidity_rank <= 20).sum())}  B={int((b.liquidity_rank <= 20).sum())}",
             f"top-50 coins: A={int((a.liquidity_rank <= 50).sum())}  B={int((b.liquidity_rank <= 50).sum())}"]
    tot = float(df.early_days.sum() + df.late_days.sum())
    for name, d, col in (("explore (early, A)", a, "early_days"), ("late_A", a, "late_days"),
                         ("early_B", b, "early_days"), ("late_B", b, "late_days")):
        n = float(d[col].sum())
        lines.append(f"coin-days {name:<20}{n:>9.0f}  ({100 * n / tot:4.1f}%)")
    return "\n".join(lines)


def main() -> None:
    df = build()
    ASSIGNMENT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(ASSIGNMENT, index=False)
    print(balance_report(df))
    print("written", ASSIGNMENT.relative_to(REPO))


if __name__ == "__main__":
    main()
