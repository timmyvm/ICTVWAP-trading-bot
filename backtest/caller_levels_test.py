"""
v0.37-exp part G — do the caller's own pre-open levels carry information? (DEVLOG v0.37-exp, part G)

Rules come from backtest/data_cache/local/discord/v036/levels_frozen.jsonl (discord_levels.py: two blind
passes, agreed rules only). Scored on the v0.35 QQQ path (HistData NSXUSD 1m x the daily QQQ ratio; Yahoo
QQQ 1m after September 2026; options_signal_fallback.Underlying).

Replay of one rule ("above L, UP"; "below L, DOWN" mirrors it):
  trigger  the first bar from 09:30 to 11:58 that closes above L after testing it (low <= L) or crossing
           it (previous close <= L); entry at the next bar's open plus slippage
  exits    his first target, if it lies beyond the entry: a limit that fills when a later bar trades through
           it (high > T), at T; a close back below L: the next bar's open minus slippage; otherwise the
           15:50 bar's open. A target touch in the same bar as a stop close fills first (the limit rests).
  costs    0.005 % of price per market fill, 0.001 % per limit fill
Population: rules on QQQ, plus UNKNOWN rules whose level is within 3 % of that session's QQQ open.

  G1  mean net return per trade > 0 with t >= 2.0, clustered by ISO (year, week)
  G2  his mean beats >= 95 % of 1,000 placebo runs with every level and its targets shifted by
      U(+-0.1 %, +-0.5 %) (one draw per rule)
  P   (secondary, no verdict) the textbook version of his method on every session: pivot = previous
      session's TPO POC ($0.05 bins), above -> UP to the previous high, below -> DOWN to the previous low

  python3 backtest/caller_levels_test.py --selftest
  python3 backtest/caller_levels_test.py --report
"""

import argparse
import json
import math
import random
import sys
from datetime import date, time
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

sys.path.insert(0, ".")
from backtest.options_signal_audit import NY, cluster_t, week_key  # noqa: E402

V036 = "backtest/data_cache/local/discord/v036"
MKT_COST, LMT_COST = 0.00005, 0.00001
LAST_TRIGGER = time(11, 58)
TIME_STOP = time(15, 50)
PLACEBO_RUNS, SHIFT_LO, SHIFT_HI = 1000, 0.001, 0.005
G1_T = 2.0


def replay_rule(bars: pd.DataFrame, level: float, side: str, direction: str,
                target: Optional[float]) -> Optional[dict]:
    """One rule on one session's 1m bars (09:30 onward). None when it never triggers."""
    up = direction == "UP"
    o, h, l, c = (bars[k].to_numpy() for k in ("o", "h", "l", "c"))
    times = bars.index.time
    n = len(bars)
    for i in range(n - 1):
        if times[i] > LAST_TRIGGER:
            return None
        prev = c[i - 1] if i > 0 else None
        if up:
            fired = c[i] > level and (l[i] <= level or (prev is not None and prev <= level))
        else:
            fired = c[i] < level and (h[i] >= level or (prev is not None and prev >= level))
        if fired:
            break
    else:
        return None
    e = i + 1
    entry = o[e] * (1 + MKT_COST if up else 1 - MKT_COST)
    tgt = target if target is not None and ((up and target > o[e]) or (not up and target < o[e])) else None
    exit_px, reason, j = None, "time stop", e
    for j in range(e, n):
        if times[j] >= TIME_STOP:
            exit_px = o[j] * (1 - MKT_COST if up else 1 + MKT_COST)
            break
        if tgt is not None and ((up and h[j] > tgt) or (not up and l[j] < tgt)):
            exit_px, reason = tgt * (1 - LMT_COST if up else 1 + LMT_COST), "target"
            break
        if (up and c[j] < level) or (not up and c[j] > level):
            if j + 1 < n:
                exit_px, reason = o[j + 1] * (1 - MKT_COST if up else 1 + MKT_COST), "stop"
                j += 1
            else:
                exit_px, reason = c[j] * (1 - MKT_COST if up else 1 + MKT_COST), "stop"
            break
    if exit_px is None:
        exit_px = c[n - 1] * (1 - MKT_COST if up else 1 + MKT_COST)
    ret = (exit_px / entry - 1) if up else (entry / exit_px - 1)
    return {"ret": ret, "reason": reason, "t_in": bars.index[e], "has_target": tgt is not None}


def tpo_poc(bars: pd.DataFrame, step: float = 0.05) -> float:
    """Time-at-price point of control: the $0.05 bin covered by the most 1m bars (ties -> nearest the mid)."""
    lo, hi = float(bars["l"].min()), float(bars["h"].max())
    edges = np.arange(math.floor(lo / step) * step, hi + step, step)
    counts = np.zeros(len(edges))
    for a, b in zip(bars["l"].to_numpy(), bars["h"].to_numpy()):
        counts[int((a - edges[0]) // step): int((b - edges[0]) // step) + 1] += 1
    best = np.flatnonzero(counts == counts.max())
    mid = (lo + hi) / 2
    k = best[np.argmin(np.abs(edges[best] + step / 2 - mid))]
    return float(edges[k] + step / 2)


def placebo_shift(rng: random.Random) -> float:
    s = rng.uniform(SHIFT_LO, SHIFT_HI)
    return s if rng.random() < 0.5 else -s


def summarize(rets: List[float], dates: List[date]) -> dict:
    x = np.array(rets)
    if not len(x):
        return {"n": 0}
    m, t = cluster_t(x, np.array([week_key(d) for d in dates]))
    pos, neg = x[x > 0].sum(), -x[x < 0].sum()
    return {"n": len(x), "mean": m, "t": t, "win": float((x > 0).mean()), "pf": float(pos / neg) if neg > 0 else float("inf")}


def line(label: str, s: dict) -> str:
    if not s.get("n"):
        return f"  {label:44s} n 0"
    return (f"  {label:44s} n {s['n']:4d}  mean {1e4 * s['mean']:+6.1f} bp  t {s['t']:+5.2f}  win {100 * s['win']:5.1f}%  "
            f"PF {s['pf']:5.2f}")


def report() -> int:
    from backtest.options_signal_fallback import Underlying
    ub = Underlying()
    dmap = {int(k): date.fromisoformat(v) for k, v in json.load(open(f"{V036}/bias_daymap.json")).items()}
    frozen = [json.loads(x) for x in open(f"{V036}/levels_frozen.jsonl", encoding="utf-8") if x.strip()]
    pop, skipped = [], {}
    for row in frozen:
        d = dmap[row["day"]]
        b = ub.day(d)
        for r in row["rules"]:
            if b is None:
                skipped["no bars"] = skipped.get("no bars", 0) + 1
                continue
            o = float(b["o"].iloc[0])
            ok = r["instrument"] == "QQQ" or (r["instrument"] == "UNKNOWN" and abs(r["level"] / o - 1) <= 0.03)
            if not ok:
                skipped[r["instrument"]] = skipped.get(r["instrument"], 0) + 1
                continue
            pop.append((d, b, r))
    print(f"frozen rules {sum(len(x['rules']) for x in frozen)}; scored population {len(pop)}; not scored {skipped}")

    def run(shift: Optional[random.Random] = None) -> Tuple[List[float], List[date], List[str]]:
        rets, dates, reasons = [], [], []
        for d, b, r in pop:
            k = 1 + placebo_shift(shift) if shift is not None else 1.0
            tgt = r["targets"][0] * k if r["targets"] else None
            out = replay_rule(b, r["level"] * k, r["side"], r["direction"], tgt)
            if out is not None:
                rets.append(out["ret"]); dates.append(d); reasons.append(out["reason"])
        return rets, dates, reasons

    rets, dates, reasons = run()
    s = summarize(rets, dates)
    print("=" * 100 + "\nG: his own pre-open levels on QQQ\n" + "=" * 100)
    print(line("G1 all triggered rules", s) + f"   triggered {len(rets)} of {len(pop)}")
    print(f"  exits: {pd.Series(reasons).value_counts().to_dict()}")
    by_dir: Dict[str, Tuple[List[float], List[date]]] = {"UP": ([], []), "DOWN": ([], [])}
    with_t: Tuple[List[float], List[date]] = ([], [])
    for d, b, r in pop:
        out = replay_rule(b, r["level"], r["side"], r["direction"], r["targets"][0] if r["targets"] else None)
        if out is None:
            continue
        by_dir[r["direction"]][0].append(out["ret"]); by_dir[r["direction"]][1].append(d)
        if out["has_target"]:
            with_t[0].append(out["ret"]); with_t[1].append(d)
    for k, (x, dd) in by_dir.items():
        print(line(f"   {k} rules", summarize(x, dd)))
    print(line("   rules with a valid first target", summarize(*with_t)))
    for y in sorted({d.year for d in dates}):
        idx = [i for i, d in enumerate(dates) if d.year == y]
        print(line(f"   {y}", summarize([rets[i] for i in idx], [dates[i] for i in idx])))
    rng = random.Random(37)
    plac = []
    for _ in range(PLACEBO_RUNS):
        pr, pdts, _ = run(rng)
        plac.append(float(np.mean(pr)) if pr else float("nan"))
    plac_a = np.array([p for p in plac if np.isfinite(p)])
    pct = float((plac_a < s["mean"]).mean()) if s.get("n") else float("nan")
    print(f"  G2 placebo levels (n runs {len(plac_a)}): mean of means {1e4 * plac_a.mean():+.1f} bp, 95th pct "
          f"{1e4 * np.percentile(plac_a, 95):+.1f} bp; his mean beats {100 * pct:.1f}% of placebo runs")
    g1 = bool(s.get("n") and s["mean"] > 0 and s["t"] >= G1_T)
    g2 = bool(pct >= 0.95)

    print("\n" + "=" * 100 + "\nP (secondary): previous-session TPO POC pivot on every session in his era\n" + "=" * 100)
    sess = [d for d in ub.sessions() if date(2024, 12, 1) <= d]
    prets, pdates, preasons = [], [], []
    prev_b = None
    for d in sess:
        b = ub.day(d)
        if b is None:
            prev_b = None
            continue
        if prev_b is not None:
            poc = tpo_poc(prev_b)
            for side, dr, tgt in (("above", "UP", float(prev_b["h"].max())), ("below", "DOWN", float(prev_b["l"].min()))):
                out = replay_rule(b, poc, side, dr, tgt)
                if out is not None:
                    prets.append(out["ret"]); pdates.append(d); preasons.append(out["reason"])
        prev_b = b
    print(line("P previous-session POC, both directions", summarize(prets, pdates)) +
          f"   exits {pd.Series(preasons).value_counts().to_dict()}")

    print("\n" + "=" * 100 + "\nVERDICT (part G)\n" + "=" * 100)
    print(f"  G1 his levels make money: {'PASS' if g1 else 'FAIL'} (mean {1e4 * s.get('mean', float('nan')):+.1f} bp, "
          f"t {s.get('t', float('nan')):+.2f})")
    print(f"  G2 his levels beat shifted levels: {'PASS' if g2 else 'FAIL'} (beats {100 * pct:.1f}%)")
    print(f"  part G: {'PASS' if g1 and g2 else 'FAIL'}")
    print("LEVELS_REPORT_DONE")
    return 0


def selftest() -> int:
    ok = True

    def check(name: str, cond: bool) -> None:
        nonlocal ok
        ok &= bool(cond)
        print(f"{'PASS' if cond else 'FAIL'}  {name}")

    idx = pd.date_range("2025-09-16 09:30", "2025-09-16 15:59", freq="1min", tz=NY)

    def bars(path: List[float]) -> pd.DataFrame:
        p = np.array(path + [path[-1]] * (len(idx) - len(path)))
        return pd.DataFrame({"o": p, "h": p + 0.02, "l": p - 0.02, "c": p}, index=idx)

    b = bars([99.0, 99.5, 100.5, 101.0, 102.0, 103.0])
    r = replay_rule(b, 100.0, "above", "UP", 102.5)
    check("cross above -> entry at the next open", r is not None and r["t_in"] == idx[3])
    check("target fills at T on a trade-through", r["reason"] == "target"
          and abs(r["ret"] - (102.5 * (1 - LMT_COST) / (101.0 * (1 + MKT_COST)) - 1)) < 1e-12)
    b2 = bars([100.5, 100.3, 100.1, 99.5, 99.0])
    b2.iloc[1, b2.columns.get_loc("l")] = 99.98
    r2 = replay_rule(b2, 100.0, "above", "UP", None)
    check("test and hold (low <= L < close) triggers", r2 is not None and r2["t_in"] == idx[2])
    check("a close back below L stops out at the next open", r2["reason"] == "stop")
    check("no close beyond L -> no trade", replay_rule(bars([99.0] * 10), 100.0, "above", "UP", None) is None)
    b3 = bars([101.0, 99.5, 99.0, 98.0, 97.0])
    b3.iloc[0, b3.columns.get_loc("h")] = 101.05
    r3 = replay_rule(b3, 100.0, "below", "DOWN", 97.5)
    check("DOWN mirror: cross below, target below", r3 is not None and r3["reason"] == "target" and r3["ret"] > 0)
    late = bars([99.0] * 160 + [101.0] * 10)
    check("no trigger after 11:58", replay_rule(late, 100.0, "above", "UP", None) is None)
    ts = replay_rule(bars([99.0, 101.0]), 100.0, "above", "UP", None)
    check("no target -> time stop at 15:50", ts["reason"] == "time stop")
    passed = replay_rule(bars([99.0, 101.0, 102.0]), 100.0, "above", "UP", 100.5)
    check("a target already passed at entry is ignored", passed["has_target"] is False)
    same = bars([99.0, 101.0, 101.0])
    same.iloc[2, same.columns.get_loc("h")] = 101.6
    same.iloc[2, same.columns.get_loc("c")] = 99.5
    r4 = replay_rule(same, 100.0, "above", "UP", 101.5)
    check("target touch and stop close in one bar -> the target fills first", r4["reason"] == "target")
    prof = pd.DataFrame({"o": [100.0] * 5, "h": [100.1, 100.1, 100.1, 100.5, 101.0], "l": [99.9, 99.9, 99.9, 99.9, 100.4],
                         "c": [100.0] * 5}, index=idx[:5])
    check("TPO POC lies in the block where most bars overlap", 99.9 <= tpo_poc(prof) <= 100.15)
    rng = random.Random(1)
    sh = [abs(placebo_shift(rng)) for _ in range(1000)]
    check("placebo shifts lie in [0.1 %, 0.5 %]", min(sh) >= SHIFT_LO and max(sh) <= SHIFT_HI)
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.report:
        return report()
    return 0


if __name__ == "__main__":
    sys.exit(main())
