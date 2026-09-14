"""
v0.22-exp — 4H bias / 30m pullback / supply-demand zone / 5m structure shift -> VWAP.

User's rule (DEVLOG v0.22-exp, pre-registered before this ran):
  4H bias up, 30m bias DOWN (the pullback), wait for price to hit a 30m
  demand zone, take a 5m structure shift as the trigger, target session VWAP.
  Mirror for shorts. The "watch the tape / exhaustion / absorption" leg is
  order flow and is ABSENT here — OHLCV klines cannot represent it.

Everything below is fixed a priori and is NOT tuned. See the DEVLOG entry for
the pass bar and for the seven specification constants that make up the
overfitting surface.
"""

import argparse
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, ".")
from backtest.data import NY_TZ, load_cached_1m, resample_ohlcv  # noqa: E402

# --- fixed specification constants (pre-registered, never tuned) ---
SWING_K = 2              # fractal half-width; a swing at j is confirmed at j+2
IMP_N = 3                # bars allowed for the departure from a zone base
IMP_MULT = 1.5           # departure must exceed this many ATR from the base
ZONE_MAX_AGE = 100       # 30m bars a zone stays live (~2 days)
MSS_WINDOW = 24          # 5m bars after a touch in which the shift must happen
STOP_BUF_ATR = 0.1       # stop buffer beyond the swing, in 5m ATR
ATR_PERIOD = 14

RISK_PCT, MAX_LEV = 1.0, 10.0
TAKER, SLIP = 0.055, 0.01


def resample_30m(df1m: pd.DataFrame) -> pd.DataFrame:
    """30m bars anchored in UTC like every other frame here (backtest/data.py)."""
    utc = df1m.tz_convert("UTC")
    out = utc.resample("30min", label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    )
    return out.dropna(subset=["open"]).tz_convert(NY_TZ)


def atr(df: pd.DataFrame, period: int = ATR_PERIOD) -> np.ndarray:
    close = df["close"]
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - close.shift()).abs(),
        (df["low"] - close.shift()).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean().to_numpy()


def confirmed_swings(df: pd.DataFrame, k: int = SWING_K) -> tuple:
    """
    (last_high_idx, last_high_px, last_low_idx, last_low_px) per bar, using only
    swings CONFIRMED by that bar. A swing at j needs k bars on each side, so it
    is unknown until j+k — anything else is lookahead.
    """
    h, low = df["high"].to_numpy(), df["low"].to_numpy()
    n = len(df)
    hi_idx = np.full(n, -1, dtype=int)
    lo_idx = np.full(n, -1, dtype=int)
    cur_hi = cur_lo = -1
    for i in range(n):
        j = i - k                                   # the bar that becomes confirmable now
        if j - k >= 0:
            if h[j] == h[j - k:j + k + 1].max():
                cur_hi = j
            if low[j] == low[j - k:j + k + 1].min():
                cur_lo = j
        hi_idx[i], lo_idx[i] = cur_hi, cur_lo
    hi_px = np.where(hi_idx >= 0, h[hi_idx], np.nan)
    lo_px = np.where(lo_idx >= 0, low[lo_idx], np.nan)
    return hi_idx, hi_px, lo_idx, lo_px


def structure_bias(df: pd.DataFrame, k: int = SWING_K) -> np.ndarray:
    """+1 bullish / -1 bearish / 0 neutral, as known at each bar's CLOSE."""
    c = df["close"].to_numpy()
    _, hi_px, _, lo_px = confirmed_swings(df, k)
    bias = np.zeros(len(df), dtype=int)
    state = 0
    for i in range(len(df)):
        if not np.isnan(hi_px[i]) and c[i] > hi_px[i]:
            state = 1
        elif not np.isnan(lo_px[i]) and c[i] < lo_px[i]:
            state = -1
        bias[i] = state
    return bias


def build_zones(df30: pd.DataFrame) -> list:
    """
    Demand/supply zones on the 30m. A demand base is a bearish candle that price
    departs from by >= IMP_MULT x ATR within IMP_N bars; the zone is the base
    candle's full range. Knowable only at b+IMP_N. Returns dicts with the bar
    index at which the zone becomes usable.
    """
    o, h = df30["open"].to_numpy(), df30["high"].to_numpy()
    low, c = df30["low"].to_numpy(), df30["close"].to_numpy()
    a = atr(df30)
    zones = []
    for b in range(ATR_PERIOD, len(df30) - IMP_N):
        if np.isnan(a[b]) or a[b] <= 0:
            continue
        up = h[b + 1:b + 1 + IMP_N].max()
        dn = low[b + 1:b + 1 + IMP_N].min()
        side = 0
        if c[b] < o[b] and up >= h[b] + IMP_MULT * a[b]:
            side = 1
        elif c[b] > o[b] and dn <= low[b] - IMP_MULT * a[b]:
            side = -1
        if side == 0:
            continue
        start, until = b + IMP_N, b + IMP_N + ZONE_MAX_AGE
        # invalidation: the first 30m CLOSE through the far side kills the zone.
        # Precomputed, but only ever consulted once the loop reaches that bar,
        # so it is a lookup and not lookahead.
        dead_at = until + 1
        for m in range(start, min(until, len(df30) - 1) + 1):
            if (side == 1 and c[m] < low[b]) or (side == -1 and c[m] > h[b]):
                dead_at = m
                break
        zones.append({"side": side, "lo": low[b], "hi": h[b],
                      "from": start, "until": until, "dead_at": dead_at})
    return zones


def session_vwap(df5: pd.DataFrame) -> np.ndarray:
    """Session VWAP matching strategy/vwap.py: typical price, cumulative, 00:00 NY reset."""
    tp = (df5["high"] + df5["low"] + df5["close"]) / 3.0
    vol = df5["volume"].replace(0, np.nan)
    day = df5.index.normalize()
    pv = (tp * vol).groupby(day).cumsum()
    cv = vol.groupby(day).cumsum()
    return (pv / cv).to_numpy()


def simulate(df1m: pd.DataFrame, start_bal: float = 10_000.0,
             taker_pct: float = TAKER, slip_pct: float = SLIP,
             target: str = "vwap") -> dict:
    # target: "vwap" = the user's rule (dynamic session VWAP).
    #         "rr2"  = DIAGNOSTIC D1 only (fixed 2R bracket) — not adoptable,
    #         it exists to separate an entry fault from a target fault.
    assert target in ("vwap", "rr2")
    df4 = resample_ohlcv(df1m, "4h")
    df30 = resample_30m(df1m)
    df5 = resample_ohlcv(df1m, "5m")

    bias4 = structure_bias(df4)
    bias30 = structure_bias(df30)
    zones = build_zones(df30)
    vwap = session_vwap(df5)
    a5 = atr(df5)

    i5 = df5.index
    o5, h5 = df5["open"].to_numpy(), df5["high"].to_numpy()
    l5, c5 = df5["low"].to_numpy(), df5["close"].to_numpy()
    day5 = i5.normalize()
    hi5_idx, hi5_px, lo5_idx, lo5_px = confirmed_swings(df5)

    # map each 5m bar to the most recent CLOSED 4H / 30m bar
    p4 = df4.index.searchsorted(i5, side="right") - 1
    p30 = df30.index.searchsorted(i5, side="right") - 1

    slip = slip_pct / 100.0
    cost = (taker_pct + slip_pct) / 100.0
    bal = start_bal
    peak, max_dd = start_bal, 0.0
    trades: list[dict] = []

    zone_by_start: dict[int, list] = {}
    for z in zones:
        zone_by_start.setdefault(z["from"], []).append(z)
    live: list[dict] = []
    seen_upto = -1
    last_b30 = -1

    j = ATR_PERIOD + 1
    while j < len(df5) - 1:
        b30, b4 = p30[j], p4[j]
        if b30 < 0 or b4 < 0 or np.isnan(a5[j]) or a5[j] <= 0:
            j += 1
            continue

        # refresh the live zone list only when a 30m bar has closed
        if b30 != last_b30:
            while seen_upto < b30:
                seen_upto += 1
                live.extend(zone_by_start.get(seen_upto, []))
            live = [z for z in live
                    if z["until"] >= b30 and z["dead_at"] > b30 and not z.get("dead")]
            last_b30 = b30

        want = 1 if (bias4[b4] == 1 and bias30[b30] == -1) else (
            -1 if (bias4[b4] == -1 and bias30[b30] == 1) else 0)
        if want == 0:
            j += 1
            continue

        touched = None
        for z in live:
            # the 5m bar overlaps the zone: price has reached it
            if z["side"] == want and l5[j] <= z["hi"] and h5[j] >= z["lo"]:
                touched = z
                break
        if touched is None:
            j += 1
            continue
        touched["dead"] = True                      # first test consumes the zone

        # --- wait for the 5m structure shift ---
        ext = l5[j] if want == 1 else h5[j]
        trig = None
        for m in range(j + 1, min(j + 1 + MSS_WINDOW, len(df5) - 1)):
            ext = min(ext, l5[m]) if want == 1 else max(ext, h5[m])
            if want == 1:
                ref_i, ref_px = hi5_idx[m], hi5_px[m]
                if ref_i > j and not np.isnan(ref_px) and c5[m] > ref_px:
                    trig = m
                    break
            else:
                ref_i, ref_px = lo5_idx[m], lo5_px[m]
                if ref_i > j and not np.isnan(ref_px) and c5[m] < ref_px:
                    trig = m
                    break
        if trig is None:
            j += 1
            continue

        k0 = trig + 1                                # entry bar: the next 5m open
        e = o5[k0] * (1 + want * slip)
        stop = ext - want * STOP_BUF_ATR * a5[trig]
        dist = want * (e - stop)
        vw0 = vwap[k0]
        # The VWAP-at-entry skip is applied in BOTH modes, so D1 trades exactly
        # the same setups as the primary and the target is the only variable.
        if dist <= 0 or np.isnan(vw0) or want * (vw0 - e) <= 0:
            j = k0
            continue
        tgt0 = vw0 if target == "vwap" else e + want * 2.0 * dist
        assert want * (e - stop) > 0 and want * (tgt0 - e) > 0, "inverted bracket"
        q = min(bal * RISK_PCT / 100.0 / dist, bal * MAX_LEV / e)

        px = reason = None
        exit_j = None
        for m in range(k0 + 1, len(df5)):
            if day5[m] != day5[k0]:                  # VWAP reset: the target is gone
                px, reason, exit_j = c5[m - 1], "SESSION", m - 1
                break
            hit_stop = l5[m] <= stop if want == 1 else h5[m] >= stop
            tv = vwap[m] if target == "vwap" else tgt0
            hit_tgt = (not np.isnan(tv)) and (h5[m] >= tv if want == 1 else l5[m] <= tv)
            if hit_stop:
                px, reason, exit_j = stop, "STOP", m
            elif hit_tgt:
                px, reason, exit_j = tv, "TP", m
            if px is not None:
                break
        if px is None:
            break

        net = want * (px - e) * q - (e + px) * q * cost
        bal += net
        peak = max(peak, bal)
        max_dd = max(max_dd, (peak - bal) / peak)
        trades.append({
            "ts": i5[k0], "dir": "LONG" if want == 1 else "SHORT", "net": net,
            "reason": reason, "r": net / (dist * q),
            "rr_planned": abs(tgt0 - e) / dist,
            "stop_pct": 100 * dist / e,
            # round-trip cost expressed in R: a setup whose planned R:R is below
            # this cannot profit even when the target is reached exactly.
            "cost_r": (e + tgt0) * cost / dist,
            "bars_held": exit_j - k0,
        })
        j = max(exit_j, k0) + 1                      # no same-bar re-entry

    t = pd.DataFrame(trades)
    if t.empty:
        return {"n": 0}
    wins = t[t.net > 0]
    gl = -t.loc[t.net <= 0, "net"].sum()
    t["y"] = t.ts.dt.year
    per_year = {int(y): round(g.net.sum(), 0) for y, g in t.groupby("y")}
    return {
        "n": len(t), "win_pct": round(100 * len(wins) / len(t), 1),
        "net": round(t.net.sum(), 0), "end_bal": round(bal, 0),
        "pf": round(wins.net.sum() / gl, 2) if gl > 0 else float("inf"),
        "max_dd_pct": round(100 * max_dd, 1),
        "avg_R": round(t.r.mean(), 3),
        "median_rr_planned": round(t.rr_planned.median(), 2),
        "rr_below_1_pct": round(100 * (t.rr_planned < 1).mean(), 1),
        "avg_cost_per_R": round(t.cost_r.mean(), 3),
        "unwinnable_pct": round(100 * (t.rr_planned <= t.cost_r).mean(), 1),
        "avg_stop_pct_of_price": round(t.stop_pct.mean(), 3),
        "median_bars_held": int(t.bars_held.median()),
        "exit_mix_pct": (100 * t.reason.value_counts(normalize=True)).round(1).to_dict(),
        "by_dir": t.groupby("dir")["net"].agg(["count", "sum"]).round(0).to_dict(orient="index"),
        "per_year": per_year,
        "years_positive": f"{sum(1 for v in per_year.values() if v > 0)}/{len(per_year)}",
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="backtest/data_cache/local/btcusd_1m_2019_2022.csv.gz")
    ap.add_argument("--start", default=None)
    ap.add_argument("--end", default=None)
    ap.add_argument("--label", default="")
    ap.add_argument("--target", choices=["vwap", "rr2"], default="vwap",
                    help="vwap = the user's rule; rr2 = diagnostic D1 only")
    args = ap.parse_args()
    df = load_cached_1m(args.cache)
    if args.start:
        df = df[df.index >= pd.Timestamp(args.start, tz="America/New_York")]
    if args.end:
        df = df[df.index < pd.Timestamp(args.end, tz="America/New_York")]
    tag = f"[{args.label}] " if args.label else ""
    print(f"{tag}{df.index.min()} -> {df.index.max()} ({len(df)} 1m rows)", flush=True)
    print(tag, simulate(df, target=args.target), flush=True)


if __name__ == "__main__":
    main()
