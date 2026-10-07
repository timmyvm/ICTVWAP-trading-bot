"""
v0.31-exp — divergence between correlated markets, two cells (DEVLOG v0.31-exp, pre-registered).

Cell B, the reel (itstomtrades, 2 Sep 2026): gold and the dollar index (DXY) normally move against
each other. When DXY makes a big push and gold barely moves, a small DXY pullback is said to give
gold a large move against the push. HistData M1 XAUUSD and UDXUSD (clock verified in the DEVLOG).

Cell A, the user's friend: a higher-timeframe structure bias, a lower-timeframe SMT divergence (one
market takes its last pre-window swing, the correlated partner does not take the same swing), an
inversion fair value gap (IFVG) in the sweeping market's leg, a limit entry on the retrace into it,
a 2R target. Pairs: BTC/ETH (Binance 5m perps) and NQ/ES (HistData NSXUSD/SPXUSD M1 index CFDs).

Every rule and constant is fixed in the DEVLOG before the first result. Higher-timeframe bars are
matched by CLOSE time (closed_htf_index asserts it) and every bracket is asserted at creation.

  --selftest   planted setups with exact expected entries, stops and targets; mutation checks
  --report     the three pre-registered primaries, then the labelled secondaries
"""

import argparse
import sys
from dataclasses import dataclass

import numpy as np
import pandas as pd

sys.path.insert(0, ".")
from backtest.data import NY_TZ, load_cached_1m, resample_ohlcv  # noqa: E402
from backtest.horizon_harvest import COMMITTED_FUNDING  # noqa: E402
from backtest.pead_drift_test import cluster_t  # noqa: E402
from backtest.sd_vwap_experiment import (atr, closed_htf_index, confirmed_swings,  # noqa: E402
                                         structure_bias)

LOCAL = "backtest/data_cache/local"
FILES = {
    "XAUUSD": f"{LOCAL}/xauusd_histdata_1m_2019_2026.csv.gz",
    "DXY": f"{LOCAL}/udxusd_histdata_1m_2019_2026.csv.gz",
    "NQ": f"{LOCAL}/nas100_histdata_1m_2019_2026.csv.gz",
    "ES": f"{LOCAL}/spx500_histdata_1m_2019_2026.csv.gz",
    "BTC": f"{LOCAL}/sdz/um5m_BTCUSDT.csv.gz",
    "ETH": f"{LOCAL}/sdz/um5m_ETHUSDT.csv.gz",
}
FUNDING = {"BTC": COMMITTED_FUNDING["BTCUSDT"], "ETH": COMMITTED_FUNDING["ETHUSDT"]}
FRESH_FROM = pd.Timestamp("2024-01-01", tz=NY_TZ)       # the verdict era starts here

# --- shared (pre-registered) ---
RR = 2.0
STOP_ATR = 0.1           # stop buffer beyond the structural extreme, in ATR(14) of the traded bars
SWING_K = 2              # fractal half-width for swings and structure bias (as in v0.22)
PASS_T, PASS_PF = 2.39, 1.2
PASS_N = {"gold": 100, "BTC/ETH": 60, "NQ/ES": 60}

# --- Cell B (pre-registered) ---
B_RET_MIN = 30           # the push is the 30-minute log return
B_LAG_TOL_MIN = 5        # ... measured from the last close at most 5 minutes before t-30
B_Z_DAYS = 20            # z denominators: RMS over the prior 20 trading days only
B_Z_MIN_COUNT = 300      # a trading day counts if it has >= 300 valid 30-minute returns
B_Z_PUSH = 2.0           # DXY |z| for a "big push"
B_Z_HOLD = 0.5           # gold z may not be beyond 0.5 in the direction DXY implies
B_WATCH_MIN = 30         # the DXY pullback must come within 30 minutes of the push bar
B_STOP_MIN = 30          # stop beyond gold's extreme over the 30 minutes ending at the trigger
B_TIME_EXIT_MIN = 120
B_ENTRY_DELAY_MAX = 5    # the entry bar must open within 5 minutes of the trigger bar
B_GAP_EXIT_MIN = 15      # close at the last bar before a data gap longer than this
GOLD_COST = {"floor": 0.00004, "base": 0.0001, "stress": 0.0002}   # per side, fraction of price

# --- Cell A (pre-registered) ---
WIDTH = {"1m": pd.Timedelta(minutes=1), "5m": pd.Timedelta(minutes=5),
         "15m": pd.Timedelta(minutes=15), "1h": pd.Timedelta(hours=1),
         "4h": pd.Timedelta(hours=4), "1d": pd.Timedelta(days=1)}
FLAT_MIN = 16 * 60       # flat at 16:00 New York
A_GAP = pd.Timedelta(minutes=60)
MAKER, TAKER, SLIP = 0.0002, 0.00055, 0.0001       # Bybit VIP0 crypto, per side
IDX_HALF_SPREAD, IDX_SLIP = 0.00005, 0.0001        # index CFDs: half of a 0.01% spread, + slippage


@dataclass(frozen=True)
class TF:
    name: str
    htf: str
    ltf: str
    w0: int              # window start, minutes after New York midnight
    w1: int              # window end (exclusive); the limit order is cancelled here


TF_PRIMARY = TF("H4>M15", "4h", "15m", 8 * 60 + 30, 11 * 60)
TF_SECONDARY = (TF("D>H1", "1d", "1h", 3 * 60, 12 * 60),
                TF("H1>M5", "1h", "5m", 8 * 60 + 30, 11 * 60),
                TF("M15>M1", "15m", "1m", 8 * 60 + 30, 11 * 60))
PAIRS = {"BTC/ETH": ("BTC", "ETH", "5m", "crypto"), "NQ/ES": ("NQ", "ES", "1m", "index")}


# ----------------------------------------------------------------------------------------------
# shared mechanics
# ----------------------------------------------------------------------------------------------
def assert_bracket(side: int, entry: float, stop: float, target: float) -> None:
    """CLAUDE.md: assert both legs of every bracket at creation (the v0.16 sign-flip lesson)."""
    if not (side * (entry - stop) > 0 and side * (target - entry) > 0):
        raise AssertionError(f"malformed bracket side={side} entry={entry} stop={stop} target={target}")


def run_bracket(o: np.ndarray, h: np.ndarray, low: np.ndarray, c: np.ndarray, idx: pd.DatetimeIndex,
                w: int, entry: float, stop: float, tgt: float, side: int, last_ok: int,
                gap: pd.Timedelta) -> tuple:
    """
    Hold from entry bar w through bar last_ok. The stop fills on touch (or at a gapped open beyond
    it); the target is a resting limit and needs a trade THROUGH it; the target never fills on the
    entry bar; when one bar touches both, the stop wins. Held to the end: exit at the open of bar
    last_ok+1 (time exit), or at the close of the last bar before a data gap longer than `gap`.
    """
    if side * (entry - stop) <= 0:                      # filled at a gapped open beyond the stop
        return w, entry, "stop"
    for x in range(w, last_ok + 1):
        if x > w:
            if idx[x] - idx[x - 1] > gap:
                return x - 1, c[x - 1], "gap"
            if side * (o[x] - stop) <= 0:
                return x, o[x], "stop"
            if side * (o[x] - tgt) > 0:
                return x, tgt, "target"
        if (low[x] <= stop) if side == 1 else (h[x] >= stop):
            return x, stop, "stop"
        if x > w and ((h[x] > tgt) if side == 1 else (low[x] < tgt)):
            return x, tgt, "target"
    nx = last_ok + 1
    if nx < len(idx) and idx[nx] - idx[last_ok] <= gap:
        return nx, o[nx], "time"
    return last_ok, c[last_ok], "time"


def week_key(ts: pd.Series) -> np.ndarray:
    """(ISO year, ISO week) as one string: CLAUDE.md, week keys must carry the year."""
    iso = pd.DatetimeIndex(ts).isocalendar()
    return (iso["year"].astype(str) + "-W" + iso["week"].astype(str).str.zfill(2)).to_numpy()


def summarize(net: np.ndarray, weeks: np.ndarray) -> dict:
    n = len(net)
    if n == 0:
        return {"n": 0, "win": np.nan, "pf": np.nan, "mean": np.nan, "t": np.nan}
    pos, neg = net[net > 0].sum(), -net[net < 0].sum()
    m, t, _, _ = cluster_t(net, weeks) if n >= 3 else (float(np.mean(net)), np.nan, n, 0)
    return {"n": n, "win": float((net > 0).mean()), "pf": float(pos / neg) if neg > 0 else np.inf,
            "mean": float(m), "t": float(t)}


def fmt(s: dict) -> str:
    if s["n"] == 0:
        return "n 0"
    return (f"n {s['n']:5d}  win {100 * s['win']:5.1f}%  PF {s['pf']:5.2f}  "
            f"mean {s['mean']:+.3f}R  t {s['t']:+5.2f}")


def verdict(s: dict, n_min: int) -> str:
    ok = s["n"] >= n_min and s["pf"] >= PASS_PF and s["mean"] > 0 and s["t"] >= PASS_T
    return ("PASS" if ok else "FAIL") + (f"  [n>={n_min} {'yes' if s['n'] >= n_min else 'NO'}, "
                                         f"PF>={PASS_PF} {'yes' if s['pf'] >= PASS_PF else 'NO'}, "
                                         f"t>={PASS_T} {'yes' if (s['mean'] > 0 and s['t'] >= PASS_T) else 'NO'}]")


# ----------------------------------------------------------------------------------------------
# Cell B: gold vs DXY on M1
# ----------------------------------------------------------------------------------------------
def fx_day(index: pd.DatetimeIndex) -> np.ndarray:
    """Trading-day number; FX days roll at 17:00 New York."""
    d = (index.tz_convert(NY_TZ) + pd.Timedelta(hours=7)).normalize().tz_localize(None)
    return np.asarray((d - pd.Timestamp("2000-01-01")) // pd.Timedelta(days=1), dtype=np.int64)


def ret_lag(close: pd.Series, minutes: int = B_RET_MIN, tol: int = B_LAG_TOL_MIN) -> np.ndarray:
    """log(close_t / close of the last bar at or before t - minutes, if within tol minutes)."""
    lagged = close.reindex(close.index - pd.Timedelta(minutes=minutes), method="ffill",
                           tolerance=pd.Timedelta(minutes=tol))
    return np.log(close.to_numpy() / lagged.to_numpy())


def prior_day_rms(r: np.ndarray, day: np.ndarray, n_days: int = B_Z_DAYS,
                  min_count: int = B_Z_MIN_COUNT) -> np.ndarray:
    """Per bar: RMS of r over the previous n_days qualifying trading days. The bar's own day never
    contributes, so a z-score built on it carries no same-day information."""
    ok = np.isfinite(r)
    d = day - day.min()
    nd = int(d.max()) + 1
    ss = np.bincount(d[ok], weights=r[ok] ** 2, minlength=nd)
    ct = np.bincount(d[ok], minlength=nd).astype(float)
    good = np.flatnonzero(ct >= min_count)
    css = np.concatenate([[0.0], np.cumsum(ss[good])])
    cct = np.concatenate([[0.0], np.cumsum(ct[good])])
    k = np.searchsorted(good, np.arange(nd), side="left")           # qualifying days strictly before
    lo = np.maximum(k - n_days, 0)
    with np.errstate(invalid="ignore", divide="ignore"):
        sig = np.sqrt((css[k] - css[lo]) / (cct[k] - cct[lo]))
    sig[k < n_days] = np.nan
    return sig[d]


def zscore(df: pd.DataFrame) -> np.ndarray:
    r = ret_lag(df["close"])
    return r / prior_day_rms(r, fx_day(df.index))


def session_of(ts: pd.Timestamp) -> str:
    h = ts.tz_convert(NY_TZ).hour
    if h >= 18 or h < 2:
        return "Asia"
    if h < 8:
        return "London"
    return "NY AM" if h < 12 else "NY PM"


def cell_b(gold: pd.DataFrame, dxy: pd.DataFrame, divergence: bool = True, rr: float = RR,
           dxy_shift_days: int = 0) -> pd.DataFrame:
    """
    Long gold (side +1) after DXY pushes UP: z_dxy >= +2 and z_gold >= -0.5 at the close of bar t;
    within (t, t+30 min] the first DXY close below the lows of its prior 3 bars; enter at the next
    gold open; stop below gold's lowest low of the 30 minutes ending at the trigger, minus 0.1 ATR;
    target rr x risk; time exit after 120 minutes. Short gold is the mirror image.
    """
    if dxy_shift_days:
        dxy = dxy.copy()
        dxy.index = dxy.index + pd.Timedelta(days=dxy_shift_days)
    zg = pd.Series(zscore(gold), gold.index)
    zd = pd.Series(zscore(dxy), dxy.index)

    ts_d = dxy.index
    dl, dh, dc = (dxy[k].to_numpy() for k in ("low", "high", "close"))
    n_d = len(dxy)
    pull_up, pull_dn = np.zeros(n_d, bool), np.zeros(n_d, bool)
    if n_d > 3:
        lo3 = np.minimum(np.minimum(dl[2:-1], dl[1:-2]), dl[:-3])
        hi3 = np.maximum(np.maximum(dh[2:-1], dh[1:-2]), dh[:-3])
        cont = np.asarray((ts_d[3:] - ts_d[:-3]) == pd.Timedelta(minutes=3))
        pull_up[3:] = (dc[3:] < lo3) & cont                          # pullback after an UP push
        pull_dn[3:] = (dc[3:] > hi3) & cont

    J = gold.index.intersection(dxy.index)
    zgJ, zdJ = zg.reindex(J).to_numpy(), zd.reindex(J).to_numpy()
    pu = pd.Series(pull_up, ts_d).reindex(J).to_numpy(dtype=bool)
    pdn = pd.Series(pull_dn, ts_d).reindex(J).to_numpy(dtype=bool)
    with np.errstate(invalid="ignore"):
        up, dn = zdJ >= B_Z_PUSH, zdJ <= -B_Z_PUSH
        if divergence:
            up &= zgJ >= -B_Z_HOLD
            dn &= zgJ <= B_Z_HOLD

    go, gh, gl, gc = (gold[k].to_numpy() for k in ("open", "high", "low", "close"))
    gidx = gold.index
    gatr = atr(gold)
    lo30 = gold["low"].rolling(f"{B_STOP_MIN}min").min().to_numpy()
    hi30 = gold["high"].rolling(f"{B_STOP_MIN}min").max().to_numpy()
    cnt30 = gold["low"].rolling(f"{B_STOP_MIN}min").count().to_numpy()
    gpos = gidx.get_indexer(J)

    push = np.flatnonzero(up | dn)
    rows, skipped = [], 0
    p = 0
    while p < len(push):
        q = push[p]
        t = J[q]
        side = 1 if up[q] else -1
        pull = pu if side == 1 else pdn
        q_end = J.searchsorted(t + pd.Timedelta(minutes=B_WATCH_MIN), side="right")
        hits = np.flatnonzero(pull[q + 1:q_end])
        if len(hits) == 0:                                          # no pullback: the watch expires
            p = np.searchsorted(push, q_end)
            continue
        uq = q + 1 + int(hits[0])
        u = J[uq]
        gu = gpos[uq]
        ge = gu + 1
        if ge >= len(gidx) or gidx[ge] - u > pd.Timedelta(minutes=B_ENTRY_DELAY_MAX) or cnt30[gu] < 20:
            skipped += 1
            p = np.searchsorted(push, uq + 1)
            continue
        ext = lo30[gu] if side == 1 else hi30[gu]
        stop = ext - side * STOP_ATR * gatr[gu]
        entry = go[ge]
        risk = side * (entry - stop)
        if not np.isfinite(stop) or risk <= 0:
            skipped += 1
            p = np.searchsorted(push, uq + 1)
            continue
        tgt = entry + side * rr * risk
        assert_bracket(side, entry, stop, tgt)
        last_ok = gidx.searchsorted(gidx[ge] + pd.Timedelta(minutes=B_TIME_EXIT_MIN), side="left") - 1
        xb, xp, why = run_bracket(go, gh, gl, gc, gidx, ge, entry, stop, tgt, side, last_ok,
                                  pd.Timedelta(minutes=B_GAP_EXIT_MIN))
        rows.append({"push_time": t, "trigger_time": u, "entry_time": gidx[ge], "exit_time": gidx[xb],
                     "side": side, "z_dxy": zdJ[q], "z_gold": zgJ[q], "entry": entry, "stop": stop,
                     "target": tgt, "exit": xp, "reason": why, "risk": risk,
                     "gross_R": side * (xp - entry) / risk})
        p = np.searchsorted(push, J.searchsorted(gidx[xb], side="right"))
    out = pd.DataFrame(rows)
    out.attrs["skipped"] = skipped
    return out


def gold_net(tr: pd.DataFrame, per_side: float) -> np.ndarray:
    return (tr["gross_R"] - per_side * (tr["entry"] + tr["exit"]) / tr["risk"]).to_numpy()


# ----------------------------------------------------------------------------------------------
# Cell A: SMT + IFVG
# ----------------------------------------------------------------------------------------------
def bars(df: pd.DataFrame, rule: str, base: str) -> pd.DataFrame:
    return df if rule == base else resample_ohlcv(df, rule)


def load_funding_ts(path: str) -> pd.Series:
    f = pd.read_csv(path)
    return pd.Series(f["rate"].to_numpy(), pd.DatetimeIndex(pd.to_datetime(f["timestamp"], unit="s", utc=True)))


def cell_a(frames: tuple, names: tuple, base: str, kind: str, tf: TF, variant: str = "primary",
           target: str = "2R", partner_shift_days: int = 0, funding: tuple = (None, None)) -> pd.DataFrame:
    """
    variant: primary | nosmt (partner ignored) | noifvg (market entry after the SMT bar) |
             nobias (both directions) — one stage changed at a time.
    target:  2R (primary) | 3R | liq (nearest pre-window liquidity at >= 2R, else 2R).
    """
    fa, fb = frames
    if partner_shift_days:
        fb = fb.copy()
        fb.index = fb.index + pd.Timedelta(days=partner_shift_days)
    L = [bars(x, tf.ltf, base) for x in (fa, fb)]
    idx = L[0].index.intersection(L[1].index)
    L = [x.loc[idx] for x in L]
    wl, wh = WIDTH[tf.ltf], WIDTH[tf.htf]
    bias = []
    for x in (fa, fb):
        H = bars(x, tf.htf, base)
        pos = closed_htf_index(H.index, wh, idx, wl)
        sb = structure_bias(H, SWING_K)
        bias.append(np.where(pos >= 0, sb[np.maximum(pos, 0)], 0))
    O = [x["open"].to_numpy() for x in L]
    Hh = [x["high"].to_numpy() for x in L]
    Lw = [x["low"].to_numpy() for x in L]
    C = [x["close"].to_numpy() for x in L]
    SW = [confirmed_swings(x, SWING_K) for x in L]
    AT = [atr(x) for x in L]

    mins = np.asarray(idx.hour * 60 + idx.minute)
    in_win = (mins >= tf.w0) & (mins < tf.w1) & np.asarray(idx.weekday < 5)
    win_pos = np.flatnonzero(in_win)
    if len(win_pos) == 0:
        return pd.DataFrame()
    days = idx.normalize()
    dw = days[win_pos]
    groups = np.split(win_pos, np.flatnonzero(np.asarray(dw[1:] != dw[:-1])) + 1)

    rows = []
    stats = {"days": 0, "smt": 0, "ifvg": 0, "unfilled": 0, "cancelled": 0}
    for g in groups:
        s, e = int(g[0]), int(g[-1]) + 1
        r = s - 1
        if r < 100 or idx[r] + wl != idx[s]:
            continue
        stats["days"] += 1
        day = days[s]
        last_ok = idx.searchsorted(day + pd.Timedelta(minutes=FLAT_MIN), side="left") - 1

        cands = []
        for a in (0, 1):
            b = 1 - a
            for dr in (1, -1):
                if variant != "nobias" and bias[a][r] != dr:
                    continue
                j, ref = (SW[a][2][r], SW[a][3][r]) if dr == 1 else (SW[a][0][r], SW[a][1][r])
                if j < SWING_K or not np.isfinite(ref):
                    continue
                seg = Lw[a][j + 1:s] if dr == 1 else Hh[a][j + 1:s]
                if len(seg) and ((seg.min() < ref) if dr == 1 else (seg.max() > ref)):
                    continue                                        # level already taken pre-window
                lo_j, hi_j = j - SWING_K, j + SWING_K + 1
                if dr == 1:
                    cref = Lw[b][lo_j:hi_j].min()
                    segb = Lw[b][hi_j:s]
                    intact_b = len(segb) == 0 or segb.min() >= cref
                else:
                    cref = Hh[b][lo_j:hi_j].max()
                    segb = Hh[b][hi_j:s]
                    intact_b = len(segb) == 0 or segb.max() <= cref
                if variant != "nosmt" and not intact_b:
                    continue
                cands.append([a, dr, j, ref, cref, True])

        setup = None
        for t in range(s, e):
            for cnd in cands:
                a, dr, j, ref, cref, alive = cnd
                if not alive:
                    continue
                if not ((Lw[a][t] < ref) if dr == 1 else (Hh[a][t] > ref)):
                    continue
                cnd[5] = False                                      # only the first sweep counts
                b = 1 - a
                holds = variant == "nosmt" or (
                    (Lw[b][s:t + 1].min() >= cref) if dr == 1 else (Hh[b][s:t + 1].max() <= cref))
                if holds:
                    setup = (a, dr, j, ref, t)
                    break
            if setup:
                break
        if setup is None:
            continue
        stats["smt"] += 1
        a, dr, j, ref, ts_ = setup

        if variant == "noifvg":
            w = ts_ + 1
            if w >= e:
                continue
            ext = Lw[a][ts_] if dr == 1 else Hh[a][ts_]
            stop = ext - dr * STOP_ATR * AT[a][ts_]
            E = O[a][w]
            risk = dr * (E - stop)
            if not np.isfinite(stop) or risk <= 0:
                continue
            P, entry_kind, v, i_f = E, "market", ts_, -1
        else:
            seg = Hh[a][j:ts_ + 1] if dr == 1 else Lw[a][j:ts_ + 1]
            k_rev = int(np.argmax(seg[::-1])) if dr == 1 else int(np.argmin(seg[::-1]))
            leg_start = j + len(seg) - 1 - k_rev
            ext = Lw[a][ts_] if dr == 1 else Hh[a][ts_]
            ext_bar = ts_
            inv = None
            for v in range(ts_ + 1, e):
                best = None
                for i in range(leg_start + 2, v):
                    if i - 1 > ext_bar:
                        break
                    if dr == 1:
                        if not Hh[a][i] < Lw[a][i - 2]:
                            continue
                        edge = Lw[a][i - 2]                          # top of a bearish FVG
                        if C[a][v] > edge and (v == i + 1 or C[a][i + 1:v].max() <= edge):
                            best = (i, edge)
                    else:
                        if not Lw[a][i] > Hh[a][i - 2]:
                            continue
                        edge = Hh[a][i - 2]                          # bottom of a bullish FVG
                        if C[a][v] < edge and (v == i + 1 or C[a][i + 1:v].min() >= edge):
                            best = (i, edge)
                if (Lw[a][v] < ext) if dr == 1 else (Hh[a][v] > ext):
                    ext, ext_bar = (Lw[a][v], v) if dr == 1 else (Hh[a][v], v)
                if best is not None:
                    inv = (v, best[0], best[1])
                    break
            if inv is None:
                continue
            stats["ifvg"] += 1
            v, i_f, P = inv
            stop = ext - dr * STOP_ATR * AT[a][v]
            if not np.isfinite(stop):
                continue
            risk = dr * (P - stop)
            entry_kind = "limit"

        tgt = P + dr * RR * risk
        if target == "3R":
            tgt = P + dr * 3.0 * risk
        elif target == "liq":
            lv = [SW[a][1][r] if dr == 1 else SW[a][3][r]]
            prior = idx.searchsorted(idx[s] - pd.Timedelta(hours=24))
            lv.append(Hh[a][prior:s].max() if dr == 1 else Lw[a][prior:s].min())
            ok = [x for x in lv if np.isfinite(x) and dr * (x - tgt) >= 0]
            if ok:
                tgt = min(ok) if dr == 1 else max(ok)
        assert_bracket(dr, P, stop, tgt)

        if entry_kind == "market":
            w, E = ts_ + 1, P
        else:
            fill = None
            for w in range(v + 1, e):
                if (O[a][w] <= P) if dr == 1 else (O[a][w] >= P):
                    fill = (w, O[a][w])
                    break
                if (Hh[a][w] >= tgt) if dr == 1 else (Lw[a][w] <= tgt):
                    stats["cancelled"] += 1                          # target reached first
                    break
                if (Lw[a][w] < P) if dr == 1 else (Hh[a][w] > P):
                    fill = (w, P)
                    break
            if fill is None:
                stats["unfilled"] += 1
                continue
            w, E = fill
        if last_ok < w:
            continue
        xb, xp, why = run_bracket(O[a], Hh[a], Lw[a], C[a], idx, w, E, stop, tgt, dr, last_ok, A_GAP)

        if kind == "crypto":
            c_in = MAKER if entry_kind == "limit" else TAKER + SLIP
            c_out = MAKER if why == "target" else TAKER + SLIP
        else:
            c_in = IDX_HALF_SPREAD + (0.0 if entry_kind == "limit" else IDX_SLIP)
            c_out = IDX_HALF_SPREAD + (0.0 if why == "target" else IDX_SLIP)
        fund_R = 0.0
        fs = funding[a]
        if fs is not None:
            t0, t1 = idx[w].tz_convert("UTC"), idx[xb].tz_convert("UTC")
            due = fs[(fs.index > t0) & (fs.index <= t1)]
            fund_R = float(-dr * due.sum() * E / risk)
        gross = dr * (xp - E) / risk
        cost = (c_in * E + c_out * xp) / risk
        rows.append({"market": names[a], "side": dr, "day": day, "smt_time": idx[ts_],
                     "entry_time": idx[w], "exit_time": idx[xb], "limit": P, "entry": E, "stop": stop,
                     "target": tgt, "exit": xp, "reason": why, "risk": risk, "entry_kind": entry_kind,
                     "gross_R": gross, "cost_R": cost, "fund_R": fund_R, "net_R": gross - cost + fund_R})
    out = pd.DataFrame(rows)
    out.attrs.update(stats)
    return out


# ----------------------------------------------------------------------------------------------
# information test (secondary): forward return in the trade's direction minus the drift
# ----------------------------------------------------------------------------------------------
def info_test(tr: pd.DataFrame, base: pd.DataFrame, horizons: tuple, price_col: str = "entry") -> list:
    """Per horizon and side: mean of side*log(close(t+H)/entry) minus side*the unconditional mean
    over the same era, with week-clustered t. Base close is read as-of t+H (last bar at or before)."""
    out = []
    if tr.empty:
        return out
    close = base["close"]
    lo, hi = tr["entry_time"].min(), tr["entry_time"].max()
    era = base[(base.index >= lo) & (base.index <= hi)]
    for H in horizons:
        dt = pd.Timedelta(minutes=H)
        fwd_px = close.reindex(pd.DatetimeIndex(tr["entry_time"]) + dt, method="ffill").to_numpy()
        fwd = np.log(fwd_px / tr[price_col].to_numpy())
        ec = era["close"]
        un = np.log(ec.reindex(ec.index + dt, method="ffill").to_numpy() / era["open"].to_numpy())
        un_mean = float(np.nanmean(un))
        for side in (1, -1):
            m = (tr["side"] == side).to_numpy() & np.isfinite(fwd)
            if m.sum() < 10:
                continue
            ex = side * (fwd[m] - un_mean)
            mean, t, n, _ = cluster_t(ex, week_key(tr["entry_time"][m]))
            out.append((H, side, n, mean * 1e4, t))
    return out


# ----------------------------------------------------------------------------------------------
# self-tests
# ----------------------------------------------------------------------------------------------
def _frame(c: np.ndarray, idx: pd.DatetimeIndex) -> pd.DataFrame:
    o = np.r_[c[0], c[:-1]]
    return pd.DataFrame({"open": o, "high": np.maximum(o, c), "low": np.minimum(o, c), "close": c,
                         "volume": 0.0}, index=idx)


def _set_bar(df: pd.DataFrame, i: int, o: float, h: float, low: float, c: float) -> None:
    df.iloc[i, df.columns.get_loc("open")] = o
    df.iloc[i, df.columns.get_loc("high")] = h
    df.iloc[i, df.columns.get_loc("low")] = low
    df.iloc[i, df.columns.get_loc("close")] = c


def _plant_b(g: pd.DataFrame, d: pd.DataFrame, p0: int, side: int) -> tuple:
    """Flatten both series around p0, push DXY 50bp at p0 (side=+1: up), pull it back at p0+4,
    give gold a 1.0 wick at p0+2 and a target-crossing bar at p0+20. Returns the expected trade."""
    G0, D0 = g["close"].iloc[p0 - 200], d["close"].iloc[p0 - 200]
    for i in range(p0 - 200, p0 + 200):
        _set_bar(g, i, G0, G0, G0, G0)
        _set_bar(d, i, D0, D0, D0, D0)
    D1 = D0 * np.exp(side * 0.005)
    _set_bar(d, p0, D0, max(D0, D1), min(D0, D1), D1)
    for i in range(p0 + 1, p0 + 200):
        _set_bar(d, i, D1, D1, D1, D1)
    D2 = D1 * (1 - side * 1e-5)
    _set_bar(d, p0 + 4, D1, max(D1, D2), min(D1, D2), D2)
    for i in range(p0 + 5, p0 + 200):
        _set_bar(d, i, D2, D2, D2, D2)
    _set_bar(g, p0 + 2, G0, G0 + (1.0 if side == -1 else 0.0), G0 - (1.0 if side == 1 else 0.0), G0)
    a14 = 1.0 / 14
    stop = G0 - side * (1.0 + 0.1 * a14)
    risk = side * (G0 - stop)
    tgt = G0 + side * 2 * risk
    G1 = tgt + side * 0.5
    _set_bar(g, p0 + 20, G0, max(G0, G1), min(G0, G1), G1)
    for i in range(p0 + 21, p0 + 200):
        _set_bar(g, i, G1, G1, G1, G1)
    return g.index[p0 + 5], G0, stop, tgt


def _a_synthetic(sweep_partner: bool = False) -> tuple:
    """Six days of 15m bars on a rising zigzag (H4 bias bullish), then a planted bullish SMT + IFVG on
    day six in market A with B holding its corresponding low. Returns frames and the expectation."""
    idx = pd.date_range("2025-01-06 00:00", periods=6 * 96, freq="15min", tz="UTC").tz_convert(NY_TZ)
    hrs = np.arange(len(idx) + 1) * 0.25
    path = 100 + 0.05 * hrs + 1.0 * np.sin(2 * np.pi * (hrs - 5) / 24)

    def frame(scale: float) -> pd.DataFrame:
        p = path * scale
        o, c = p[:-1], p[1:]
        return pd.DataFrame({"open": o, "high": np.maximum(o, c) + 0.05 * scale,
                             "low": np.minimum(o, c) - 0.05 * scale, "close": c, "volume": 0.0}, index=idx)
    A, B = frame(1.0), frame(0.5)
    day = pd.Timestamp("2025-01-10", tz=NY_TZ)          # a Friday
    i0 = idx.get_loc(day + pd.Timedelta(hours=6))
    X0, Y0 = A["open"].iloc[i0], B["open"].iloc[i0]
    a_bars = [(-0.5, -0.3, -0.7, -0.5)] * 4 + [
        (-0.5, -0.4, -1.0, -0.9), (-0.9, -0.8, -1.5, -1.4), (-1.4, -1.2, -2.0, -1.6),   # 07:00-07:30
        (-1.6, -1.0, -1.7, -1.1), (-1.1, -0.6, -1.2, -0.7), (-0.7, -0.1, -0.8, -0.2),   # 07:45-08:15
        (-0.2, 0.5, -0.3, 0.3), (0.3, 0.4, -0.8, -0.7), (-0.7, -0.6, -1.9, -1.8),       # 08:30-09:00
        (-1.8, -1.2, -2.6, -2.4), (-2.4, -1.6, -2.7, -1.7), (-1.7, -0.4, -1.8, -0.5),   # 09:15-09:45
        (-0.5, -0.3, -0.9, -0.6), (-0.6, 0.5, -0.7, 0.4), (0.4, 2.0, 0.3, 1.9),         # 10:00-10:30
        (1.9, 10.0, 1.8, 9.9)]                                                          # 10:45
    b_low_0915 = -1.1 if sweep_partner else -0.85
    b_bars = [(-0.2, -0.1, -0.3, -0.2)] * 4 + [
        (-0.2, -0.1, -0.5, -0.4), (-0.4, -0.3, -0.75, -0.6), (-0.6, -0.5, -1.0, -0.7),
        (-0.7, -0.4, -0.75, -0.45), (-0.45, -0.3, -0.5, -0.35), (-0.35, -0.05, -0.4, -0.1),
        (-0.1, 0.25, -0.15, 0.15), (0.15, 0.2, -0.4, -0.35), (-0.35, -0.3, -0.7, -0.65),
        (-0.65, -0.5, b_low_0915, -0.8), (-0.8, -0.6, -0.88, -0.65), (-0.65, -0.1, -0.7, -0.15),
        (-0.15, 0.0, -0.3, -0.1), (-0.1, 0.4, -0.15, 0.35), (0.35, 1.0, 0.3, 0.9), (0.9, 5.0, 0.8, 4.9)]
    for k, (o, h, low, c) in enumerate(a_bars):
        _set_bar(A, i0 + k, X0 + o, X0 + h, X0 + low, X0 + c)
    for k, (o, h, low, c) in enumerate(b_bars):
        _set_bar(B, i0 + k, Y0 + o, Y0 + h, Y0 + low, Y0 + c)
    end = i0 + len(a_bars)
    for i in range(end, idx.get_loc(day + pd.Timedelta(hours=17))):
        _set_bar(A, i, X0 + 9.9, X0 + 9.95, X0 + 9.85, X0 + 9.9)
        _set_bar(B, i, Y0 + 4.9, Y0 + 4.95, Y0 + 4.85, Y0 + 4.9)
    v = i0 + 15                                                     # the 09:45 inversion bar
    a_v = atr(A)[v]
    stop = X0 - 2.7 - 0.1 * a_v
    E = X0 - 0.8
    tgt = E + 2 * (E - stop)
    return (A, B), {"entry_time": idx[i0 + 16], "entry": E, "stop": stop, "target": tgt,
                    "exit_time": idx[i0 + 19], "day": day}


def selftest() -> None:
    fails = 0

    def check(name: str, ok: bool) -> None:
        nonlocal fails
        fails += 0 if ok else 1
        print(f"{'PASS' if ok else 'FAIL'}  {name}")

    # --- shared mechanics ---
    try:
        assert_bracket(1, 100.0, 99.0, 98.0)
        check("mutation: a long bracket with its target below entry is rejected", False)
    except AssertionError:
        check("mutation: a long bracket with its target below entry is rejected", True)
    idx = pd.date_range("2025-01-06 15:00", periods=6, freq="1min", tz="UTC")
    o = np.array([100.0, 100.0, 100.0, 100.0, 100.0, 100.0])
    h = np.array([100.0, 103.0, 100.0, 100.0, 100.0, 100.0])
    low = np.array([100.0, 98.0, 100.0, 100.0, 100.0, 100.0])
    c = o.copy()
    r = run_bracket(o, h, low, c, idx, 0, 100.0, 99.0, 102.0, 1, 4, pd.Timedelta(minutes=15))
    check("a bar touching stop and target exits at the stop", r == (1, 99.0, "stop"))
    h2 = np.array([103.0, 100.0, 100.0, 100.0, 100.0, 100.0])
    r = run_bracket(o, h2, low * 0 + 100.0, c, idx, 0, 100.0, 99.0, 102.0, 1, 4, pd.Timedelta(minutes=15))
    check("the target never fills on the entry bar (time exit instead)", r == (5, 100.0, "time"))
    h3 = np.array([100.0, 102.0, 100.0, 100.0, 100.0, 100.0])
    r = run_bracket(o, h3, low * 0 + 100.0, c, idx, 0, 100.0, 99.0, 102.0, 1, 4, pd.Timedelta(minutes=15))
    check("a limit target needs a trade through it (a touch is not a fill)", r[2] == "time")

    # --- Cell B: z-scores use prior days only ---
    rng = np.random.default_rng(7)
    gidx = pd.date_range("2025-01-06 00:00", periods=30 * 1440, freq="1min", tz="UTC").tz_convert(NY_TZ)
    gold = _frame(2000 * np.exp(np.cumsum(rng.normal(0, 1e-4, len(gidx)))), gidx)
    dxy = _frame(100 * np.exp(np.cumsum(rng.normal(0, 1e-4, len(gidx)))), gidx)
    rr = ret_lag(gold["close"])
    day = fx_day(gidx)
    s1 = prior_day_rms(rr, day)
    rr2 = rr.copy()
    last = day == day.max()
    rr2[last] *= 100.0
    s2 = prior_day_rms(rr2, day)
    check("a day's z denominator ignores that day's own returns", bool(np.allclose(s1[last], s2[last], equal_nan=True)))
    check("no z denominator before 20 prior trading days", bool(np.isnan(s1[day < day.min() + 20]).all()))

    # --- Cell B: planted long and short divergences are traded exactly ---
    p_long, p_short = 25 * 1440 + 15 * 60, 27 * 1440 + 15 * 60
    exp_l = _plant_b(gold, dxy, p_long, 1)
    exp_s = _plant_b(gold, dxy, p_short, -1)
    tr = cell_b(gold, dxy)
    for name, (et, E, stop, tgt), side in (("long", exp_l, 1), ("short", exp_s, -1)):
        m = tr[tr["entry_time"] == et] if not tr.empty else tr
        ok = (len(m) == 1 and m["side"].iloc[0] == side and np.isclose(m["entry"].iloc[0], E)
              and np.isclose(m["stop"].iloc[0], stop) and np.isclose(m["target"].iloc[0], tgt)
              and m["reason"].iloc[0] == "target" and np.isclose(m["gross_R"].iloc[0], 2.0))
        check(f"Cell B planted {name}: entry, stop, target and the +2R exit are exact", ok)
    check("Cell B divergence filter holds on every trade (gold z inside +-0.5 against the push)",
          bool(((tr["side"] * tr["z_gold"]) >= -B_Z_HOLD - 1e-12).all()) if not tr.empty else False)
    check("Cell B push filter holds on every trade (|z_dxy| >= 2 in the trade's direction)",
          bool(((tr["side"] * tr["z_dxy"]) >= B_Z_PUSH).all()) if not tr.empty else False)
    ent = pd.DatetimeIndex(tr["entry_time"])
    ext = pd.DatetimeIndex(tr["exit_time"])
    check("Cell B never holds two positions at once", bool((ent[1:] > ext[:-1]).all()))
    check("Cell B entries come after the trigger bar", bool((tr["entry_time"] > tr["trigger_time"]).all()))
    check("Cell B time exits never exceed 120 minutes plus one bar",
          bool(((ext - ent) <= pd.Timedelta(minutes=B_TIME_EXIT_MIN + 1)).all()))
    nul = cell_b(gold, dxy, dxy_shift_days=7)
    check("Cell B null (DXY shifted a week): the planted trades disappear",
          nul.empty or not nul["entry_time"].isin([exp_l[0], exp_s[0]]).any())

    # --- Cell A: planted SMT + IFVG ---
    frames, exp = _a_synthetic()
    tr = cell_a(frames, ("A", "B"), "15m", "index", TF_PRIMARY)
    m = tr[tr["day"] == exp["day"]] if not tr.empty else tr
    ok = (len(m) == 1 and m["market"].iloc[0] == "A" and m["side"].iloc[0] == 1
          and m["entry_time"].iloc[0] == exp["entry_time"] and np.isclose(m["entry"].iloc[0], exp["entry"])
          and np.isclose(m["stop"].iloc[0], exp["stop"]) and np.isclose(m["target"].iloc[0], exp["target"])
          and m["reason"].iloc[0] == "target" and m["exit_time"].iloc[0] == exp["exit_time"]
          and np.isclose(m["gross_R"].iloc[0], 2.0))
    check("Cell A planted SMT+IFVG: A long, limit at the IFVG top, stop, 2R target and exit exact", ok)
    if not ok and not m.empty:
        print(m.T)
        print(exp)
    frames2, _ = _a_synthetic(sweep_partner=True)
    tr2 = cell_a(frames2, ("A", "B"), "15m", "index", TF_PRIMARY)
    check("Cell A mutation: when the partner also takes its low there is no SMT trade",
          tr2.empty or not (tr2["day"] == exp["day"]).any())
    tr3 = cell_a(frames2, ("A", "B"), "15m", "index", TF_PRIMARY, variant="nosmt")
    check("Cell A no-SMT ablation still takes the planted trade with the partner ignored",
          (not tr3.empty) and bool(((tr3["day"] == exp["day"]) & (tr3["entry_time"] == exp["entry_time"])).any()))
    check("Cell A costs: index limit-in/target-out pays the half spread on each side",
          len(m) == 1 and bool(np.isclose(m["cost_R"].iloc[0],
                                          IDX_HALF_SPREAD * (m["entry"].iloc[0] + m["exit"].iloc[0]) / m["risk"].iloc[0])))

    # mirror image: reflect both markets around K, so the bias, SMT and IFVG are all bearish
    K = 400.0

    def reflect(df: pd.DataFrame) -> pd.DataFrame:
        return pd.DataFrame({"open": K - df["open"], "high": K - df["low"], "low": K - df["high"],
                             "close": K - df["close"], "volume": df["volume"]}, index=df.index)
    fr = (reflect(frames[0]), reflect(frames[1]))
    trm = cell_a(fr, ("A", "B"), "15m", "index", TF_PRIMARY)
    mm = trm[trm["day"] == exp["day"]] if not trm.empty else trm
    E_s = K - exp["entry"]
    stop_s = K - exp["stop"]
    ok = (len(mm) == 1 and mm["side"].iloc[0] == -1 and mm["entry_time"].iloc[0] == exp["entry_time"]
          and np.isclose(mm["entry"].iloc[0], E_s) and np.isclose(mm["stop"].iloc[0], stop_s)
          and np.isclose(mm["target"].iloc[0], E_s - 2 * (stop_s - E_s)) and mm["reason"].iloc[0] == "target"
          and np.isclose(mm["gross_R"].iloc[0], 2.0))
    check("Cell A mirrored planted setup: the bearish SMT+IFVG short is exact", ok)

    # lookahead guard: cutting the data right after the entry bar must not change any entry decision
    cut = exp["entry_time"] + pd.Timedelta(minutes=15)
    trc = cell_a((frames[0][frames[0].index < cut], frames[1][frames[1].index < cut]), ("A", "B"), "15m",
                 "index", TF_PRIMARY)
    mc = trc[trc["day"] == exp["day"]] if not trc.empty else trc
    check("Cell A truncated after the entry bar: same entry, stop and target (no lookahead)",
          len(mc) == 1 and mc["entry_time"].iloc[0] == exp["entry_time"]
          and np.isclose(mc["entry"].iloc[0], exp["entry"]) and np.isclose(mc["stop"].iloc[0], exp["stop"])
          and np.isclose(mc["target"].iloc[0], exp["target"]))
    gcut = exp_l[0] + pd.Timedelta(minutes=1)
    trb = cell_b(gold[gold.index < gcut], dxy[dxy.index < gcut])
    mb = trb[trb["entry_time"] == exp_l[0]] if not trb.empty else trb
    check("Cell B truncated after the entry bar: same entry, stop and target (no lookahead)",
          len(mb) == 1 and np.isclose(mb["entry"].iloc[0], exp_l[1]) and np.isclose(mb["stop"].iloc[0], exp_l[2])
          and np.isclose(mb["target"].iloc[0], exp_l[3]))

    # crypto costs and the funding sign: a long held over a positive settlement pays it
    settle = exp["entry_time"] + pd.Timedelta(minutes=30)
    fz = pd.Series([0.001], pd.DatetimeIndex([settle.tz_convert("UTC")]))
    trf = cell_a(frames, ("A", "B"), "15m", "crypto", TF_PRIMARY, funding=(fz, None))
    mf = trf[trf["day"] == exp["day"]] if not trf.empty else trf
    ok = (len(mf) == 1
          and np.isclose(mf["cost_R"].iloc[0], MAKER * (mf["entry"].iloc[0] + mf["exit"].iloc[0]) / mf["risk"].iloc[0])
          and np.isclose(mf["fund_R"].iloc[0], -0.001 * mf["entry"].iloc[0] / mf["risk"].iloc[0]))
    check("Cell A crypto: maker fee on limit entry and target exit; a long pays positive funding", ok)

    print(f"\nselftest: {'ALL PASS' if fails == 0 else f'{fails} FAILED'}")
    if fails:
        sys.exit(1)


# ----------------------------------------------------------------------------------------------
# report
# ----------------------------------------------------------------------------------------------
def era_split(tr: pd.DataFrame) -> tuple:
    f = pd.DatetimeIndex(tr["entry_time"]) >= FRESH_FROM
    return tr[f], tr[~f]


def stat(tr: pd.DataFrame, net: np.ndarray) -> dict:
    return summarize(net, week_key(tr["entry_time"])) if len(tr) else summarize(np.array([]), np.array([]))


def equity_lines(tr: pd.DataFrame, net: np.ndarray, label: str) -> None:
    if not len(tr):
        return
    yr = pd.DatetimeIndex(tr["entry_time"]).year
    eq, peak, mdd = 1.0, 1.0, 0.0
    for x in net:
        eq *= 1 + 0.01 * x
        peak = max(peak, eq)
        mdd = max(mdd, 1 - eq / peak)
    by = pd.Series(net).groupby(yr).agg(["count", "mean", "sum"])
    parts = ", ".join(f"{y}: {int(r['count'])} tr {r['sum']:+.1f}%" for y, r in by.iterrows())
    print(f"  {label} at 1% risk per trade (simple sum by year): {parts}")
    print(f"  {label} compounded over the whole sample: {100 * (eq - 1):+.1f}%  max drawdown {100 * mdd:.1f}%")


def report_gold(gold: pd.DataFrame, dxy: pd.DataFrame) -> dict:
    print("\n" + "=" * 100 + "\nCELL B — the reel: gold vs DXY, M1, 2R, base costs 0.01%/side\n" + "=" * 100)
    tr = cell_b(gold, dxy)
    tr.to_csv(f"{LOCAL}/v031_gold_trades.csv", index=False)
    net = gold_net(tr, GOLD_COST["base"])
    tr = tr.assign(net_R=net, cost_R=tr["gross_R"] - net)
    fresh, old = era_split(tr)
    sf = stat(fresh, fresh["net_R"].to_numpy())
    print(f"trades {len(tr)} (skipped setups {tr.attrs.get('skipped', 0)}), "
          f"{tr['entry_time'].min()} -> {tr['entry_time'].max()}")
    print(f"PRIMARY  fresh era {FRESH_FROM.date()}+ : {fmt(sf)}  -> {verdict(sf, PASS_N['gold'])}")
    print(f"context  2019-2023           : {fmt(stat(old, old['net_R'].to_numpy()))}")
    print(f"cost share: median cost {fresh['cost_R'].median():.3f}R per trade; median risk "
          f"{100 * (fresh['risk'] / fresh['entry']).median():.3f}% of price (${fresh['risk'].median():.2f}/oz)")
    g = fresh["gross_R"].to_numpy()
    scale = ((fresh["entry"] + fresh["exit"]) / fresh["risk"]).to_numpy()
    be = g.mean() / scale.mean() if len(g) else np.nan
    print(f"gross (no costs) fresh era: {fmt(stat(fresh, g))}")
    print(f"break-even cost per side: {100 * be:.4f}% of price "
          f"(= ${be * fresh['entry'].mean():.2f}/oz at the era's mean price ${fresh['entry'].mean():,.0f})")
    print("\nSECONDARY (labelled; cannot rescue the primary)")
    for k, c in GOLD_COST.items():
        n_ = gold_net(fresh, c)
        print(f"  cost {k:6s} {100 * c:.4f}%/side: {fmt(stat(fresh, n_))}")
    for side, name in ((1, "long gold (DXY pushed up)"), (-1, "short gold (DXY pushed down)")):
        m = fresh["side"] == side
        print(f"  {name:30s}: {fmt(stat(fresh[m], fresh['net_R'][m].to_numpy()))}")
    sess = fresh["entry_time"].map(session_of)
    for sname in ("Asia", "London", "NY AM", "NY PM"):
        m = sess == sname
        print(f"  session {sname:6s}: {fmt(stat(fresh[m], fresh['net_R'][m].to_numpy()))}")
    for y, grp in tr.groupby(pd.DatetimeIndex(tr["entry_time"]).year):
        print(f"  year {y}: {fmt(stat(grp, grp['net_R'].to_numpy()))}")
    equity_lines(fresh, fresh["net_R"].to_numpy(), "fresh era")
    for label, kw in (("3R target", {"rr": 3.0}), ("no divergence filter (any DXY push)", {"divergence": False}),
                      ("NULL: DXY shifted one week", {"dxy_shift_days": 7})):
        t2 = cell_b(gold, dxy, **kw)
        f2, _ = era_split(t2)
        print(f"  {label:38s}: {fmt(stat(f2, gold_net(f2, GOLD_COST['base'])))}")
    print("  information (fresh era): direction-signed log return from the entry open, minus the era's "
          "unconditional drift, bp")
    for H, side, n, m, t in info_test(fresh, gold, (15, 60, 240)):
        print(f"    {H:4d} min {'long ' if side == 1 else 'short'}: n {n:5d}  excess {m:+7.2f} bp  t {t:+5.2f}"
              f"   (round-trip base cost {2e4 * GOLD_COST['base']:.0f} bp)")
    return {"gold": sf}


def load_pair(pair: str) -> tuple:
    a, b, base, kind = PAIRS[pair]
    fa, fb = load_cached_1m(FILES[a]), load_cached_1m(FILES[b])
    fund = (load_funding_ts(FUNDING[a]), load_funding_ts(FUNDING[b])) if kind == "crypto" else (None, None)
    return (fa, fb), (a, b), base, kind, fund


def report_pair(pair: str) -> dict:
    frames, names, base, kind, fund = load_pair(pair)
    print("\n" + "=" * 100 + f"\nCELL A — SMT + IFVG on {pair}, {TF_PRIMARY.name}, 2R\n" + "=" * 100)
    tr = cell_a(frames, names, base, kind, TF_PRIMARY, funding=fund)
    tr.to_csv(f"{LOCAL}/v031_{pair.replace('/', '')}_trades.csv", index=False)
    st = tr.attrs
    print(f"window days {st.get('days')}, SMT days {st.get('smt')}, IFVG {st.get('ifvg')}, "
          f"unfilled {st.get('unfilled')}, cancelled (target first) {st.get('cancelled')}, trades {len(tr)}")
    if tr.empty:
        print("no trades")
        return {pair: summarize(np.array([]), np.array([]))}
    fresh, old = era_split(tr)
    sf = stat(fresh, fresh["net_R"].to_numpy())
    print(f"PRIMARY  fresh era {FRESH_FROM.date()}+ : {fmt(sf)}  -> {verdict(sf, PASS_N[pair])}")
    print(f"context  before 2024           : {fmt(stat(old, old['net_R'].to_numpy()))}")
    print(f"cost share: median cost {fresh['cost_R'].median():.3f}R; median risk "
          f"{100 * (fresh['risk'] / fresh['entry']).median():.3f}% of price; funding mean {fresh['fund_R'].mean():+.4f}R")
    print(f"gross (no costs, no funding) fresh era: {fmt(stat(fresh, fresh['gross_R'].to_numpy()))}")
    print("\nSECONDARY (labelled; cannot rescue the primary)")
    for mk in names:
        m = fresh["market"] == mk
        print(f"  traded {mk:4s}: {fmt(stat(fresh[m], fresh['net_R'][m].to_numpy()))}")
    for side, nm in ((1, "long"), (-1, "short")):
        m = fresh["side"] == side
        print(f"  {nm:5s}: {fmt(stat(fresh[m], fresh['net_R'][m].to_numpy()))}")
    for y, grp in tr.groupby(pd.DatetimeIndex(tr["entry_time"]).year):
        print(f"  year {y}: {fmt(stat(grp, grp['net_R'].to_numpy()))}")
    equity_lines(fresh, fresh["net_R"].to_numpy(), "fresh era")
    runs = [("3R target", {"target": "3R"}), ("nearest liquidity >= 2R", {"target": "liq"}),
            ("ablation: no SMT (partner ignored)", {"variant": "nosmt"}),
            ("ablation: no IFVG (market entry after the SMT bar)", {"variant": "noifvg"}),
            ("ablation: no HTF bias", {"variant": "nobias"}),
            ("NULL: partner shifted one week", {"partner_shift_days": 7})]
    for label, kw in runs:
        t2 = cell_a(frames, names, base, kind, TF_PRIMARY, funding=fund, **kw)
        f2 = era_split(t2)[0] if not t2.empty else t2
        print(f"  {label:50s}: {fmt(stat(f2, f2['net_R'].to_numpy())) if len(f2) else 'n 0'}")
    for tf in TF_SECONDARY:
        if tf.ltf == "1m" and base != "1m":
            print(f"  timeframe {tf.name}: not available (no 1m data for {pair})")
            continue
        t2 = cell_a(frames, names, base, kind, tf, funding=fund)
        f2 = era_split(t2)[0] if not t2.empty else t2
        print(f"  timeframe {tf.name:7s} (window {tf.w0 // 60:02d}:{tf.w0 % 60:02d}-{tf.w1 // 60:02d}:{tf.w1 % 60:02d})"
              f": {fmt(stat(f2, f2['net_R'].to_numpy())) if len(f2) else 'n 0'}")
    base_frames = {names[0]: frames[0], names[1]: frames[1]}
    print("  information (fresh era): direction-signed log return from the fill, minus unconditional drift, bp")
    for mk in names:
        sub = fresh[fresh["market"] == mk]
        for H, side, n, m, t in info_test(sub, base_frames[mk], (60, 240)):
            print(f"    {mk:4s} {H:4d} min {'long ' if side == 1 else 'short'}: n {n:4d}  excess {m:+7.2f} bp  t {t:+5.2f}")
    return {pair: sf}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--only", choices=["gold", "BTC/ETH", "NQ/ES"], help="debug: one cell only")
    a = ap.parse_args()
    if a.selftest:
        selftest()
    if a.report:
        res = {}
        if a.only in (None, "gold"):
            res.update(report_gold(load_cached_1m(FILES["XAUUSD"]), load_cached_1m(FILES["DXY"])))
        for pair in PAIRS:
            if a.only in (None, pair):
                res.update(report_pair(pair))
        print("\n" + "=" * 100 + "\nPRE-REGISTERED VERDICTS (fresh era 2024-01-01 -> data end)\n" + "=" * 100)
        for k, s in res.items():
            print(f"  {k:8s}: {fmt(s)}  -> {verdict(s, PASS_N[k])}")


if __name__ == "__main__":
    main()
