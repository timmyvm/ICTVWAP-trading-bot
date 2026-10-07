"""
Audit a Telegram signal channel against real prices: what would a follower actually have made?

Input: a CSV of the channel's signals read from its posts (id, posted_local, utc_offset_h, symbol,
side, order, entry, tp1..tp4, sl) and an optional CSV of later "move your stop loss" instructions.
Prices: Dukascopy BID and ASK 1-minute candles (complete UTC days), plus hourly tick files for the
current day. Buys fill at the ASK and exit at the BID; sells the reverse, so the spread is paid.

Fill rules:
- market signal: the follower fills at the opening price of the minute after the post (the post
  carries minute resolution, so this is the earliest honest fill); "as stated" variant: his price.
- limit signal: fills when the ask trades at/through a buy limit (bid for a sell limit) after the
  post; a gapped open beyond the limit fills at that open.
- stop first when one minute touches both; targets never fill on the fill minute (the order of
  events inside it is unknown); stop moves apply from the minute after they were posted.

Three ways to manage the four targets, reported side by side:
- TP1: whole position out at TP1 or the stop, whichever comes first (how "win rate" is usually counted);
- TP4: whole position out at TP4 or the stop;
- split: a quarter out at each target, the remainder at the stop.
Anything still open at the data end is marked to market and listed as open.

  python3 backtest/signal_audit.py backtest/signal_audits/tsa_free_trades.csv
"""

import argparse
import glob
import lzma
import os
import struct
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, ".")
import backtest.fetch_dukascopy as fd  # noqa: E402

RAW = "backtest/data_cache/local/duka_raw_gold"
TICK = struct.Struct(">IIIff")          # ms offset, ask, bid, ask volume, bid volume
SCALE = 1000.0                          # XAUUSD points (0.001)


def load_candles(symbol: str, start: pd.Timestamp, end: pd.Timestamp) -> tuple:
    """BID and ASK 1m candles for [start, end] (UTC): daily candle files, then hourly ticks for any
    day whose candle file is not published yet (the current day)."""
    os.makedirs(RAW, exist_ok=True)
    bids, asks = [], []
    for day in pd.date_range(start.normalize().tz_localize(None), end.tz_localize(None), freq="D"):
        b = fd.fetch_day(symbol, day, "BID", RAW, delay=1.0, retries=4)
        a = fd.fetch_day(symbol, day, "ASK", RAW, delay=1.0, retries=4)
        if b is not None and a is not None:
            bids.append(b.set_index("timestamp"))
            asks.append(a.set_index("timestamp"))
            continue
        tb, ta = ticks_to_candles(symbol, day, end)
        if tb is not None:
            bids.append(tb)
            asks.append(ta)
    bid, ask = pd.concat(bids).sort_index(), pd.concat(asks).sort_index()
    keep = bid["volume"] > 0                      # Dukascopy pads closed hours with flat bars
    bid, ask = bid[keep], ask.reindex(bid.index[keep])
    return bid, ask


def ticks_to_candles(symbol: str, day: pd.Timestamp, end: pd.Timestamp) -> tuple:
    rows = []
    for h in range(24):
        t0 = pd.Timestamp(day, tz="UTC") + pd.Timedelta(hours=h)
        if t0 + pd.Timedelta(hours=1) > end:
            break
        key = os.path.join(RAW, f"{symbol}_{day.date()}_{h:02d}h_ticks.pkl")
        if os.path.exists(key):
            rows.append(pd.read_pickle(key))
            continue
        url = f"{fd.BASE}/{symbol}/{day.year}/{day.month - 1:02d}/{day.day:02d}/{h:02d}h_ticks.bi5"
        r = fd._SESSION.get(url, timeout=60)
        if r.status_code != 200 or not r.content:
            continue
        raw = lzma.decompress(r.content)
        recs = [TICK.unpack_from(raw, i * TICK.size) for i in range(len(raw) // TICK.size)]
        df = pd.DataFrame(recs, columns=["ms", "ask", "bid", "av", "bv"])
        df["ts"] = t0 + pd.to_timedelta(df["ms"], unit="ms")
        df[["ask", "bid"]] = df[["ask", "bid"]] / SCALE
        df.to_pickle(key)
        rows.append(df)
    if not rows:
        return None, None
    t = pd.concat(rows).set_index("ts")
    out = []
    for col in ("bid", "ask"):
        c = t[col].resample("1min").agg(["first", "max", "min", "last"]).dropna()
        c.columns = ["open", "high", "low", "close"]
        c["volume"] = t[col].resample("1min").count().reindex(c.index)
        out.append(c)
    return out[0], out[1]


def replay(sig: pd.Series, moves: pd.DataFrame, bid: pd.DataFrame, ask: pd.DataFrame, as_stated: bool) -> dict:
    d = 1 if sig["side"] == "buy" else -1
    tps = [float(sig[f"tp{k}"]) for k in range(1, 5)]
    sl = float(sig["sl"])
    post = (pd.Timestamp(sig["posted_local"]) - pd.Timedelta(hours=float(sig["utc_offset_h"]))).tz_localize("UTC")
    entry_side, exit_side = (ask, bid) if d == 1 else (bid, ask)
    after = entry_side.index > post
    if not after.any():
        return {"status": "no data"}
    # fill
    if sig["order"] == "market":
        i0 = int(np.argmax(after))
        fill_t = entry_side.index[i0]
        entry = float(sig["entry"]) if as_stated else float(entry_side["open"].iloc[i0])
    else:
        lim = float(sig["entry"])
        e = entry_side[after]
        hit = (e["low"] <= lim) if d == 1 else (e["high"] >= lim)
        if not hit.any():
            return {"status": "limit never filled", "post": post}
        fill_t = hit.idxmax()
        o = float(e.loc[fill_t, "open"])
        entry = min(o, lim) if d == 1 else max(o, lim)
    sl_now = sl
    mv = moves[moves["applies_to"].str.split("|").map(lambda ids: sig["id"] in ids)]
    mv_times = [(pd.Timestamp(r["posted_local"]) - pd.Timedelta(hours=float(r["utc_offset_h"]))).tz_localize("UTC")
                for _, r in mv.iterrows()]
    x = exit_side[exit_side.index >= fill_t]
    hits = {}
    stop = None
    for t, row in x.iterrows():
        for (mt, (_, r)) in zip(mv_times, mv.iterrows()):
            if t > mt and sl_now != float(r["new_sl"]) and len([k for k in hits if k.startswith("tp")]) < 4:
                sl_now = float(r["new_sl"])
        if (row["low"] <= sl_now) if d == 1 else (row["high"] >= sl_now):
            stop = (t, sl_now)
            break
        if t > fill_t:
            for k, tp in enumerate(tps, 1):
                if f"tp{k}" not in hits and ((row["high"] > tp) if d == 1 else (row["low"] < tp)):
                    hits[f"tp{k}"] = t
        if len(hits) == 4:
            break
    last = float(x["close"].iloc[-1])
    res = {"status": "closed", "post": post, "fill": fill_t, "entry": entry, "stop_at": stop, "hits": hits,
           "sl_final": sl_now, "mark": last}
    pts = lambda px: d * (px - entry)
    # TP1 rule
    if "tp1" in hits:
        res["tp1_pnl"], res["tp1_res"] = pts(tps[0]), "win"
    elif stop:
        res["tp1_pnl"], res["tp1_res"] = pts(stop[1]), "loss"
    else:
        res["tp1_pnl"], res["tp1_res"] = pts(last), "open"
    # TP4 rule
    if "tp4" in hits:
        res["tp4_pnl"], res["tp4_res"] = pts(tps[3]), "win"
    elif stop:
        res["tp4_pnl"], res["tp4_res"] = pts(stop[1]), "loss"
    else:
        res["tp4_pnl"], res["tp4_res"] = pts(last), "open"
    # split a quarter at each target
    got = [pts(tps[k - 1]) for k in range(1, 5) if f"tp{k}" in hits]
    rest = 4 - len(got)
    tail = pts(stop[1]) if stop else pts(last)
    res["split_pnl"] = (sum(got) + rest * tail) / 4.0
    res["split_res"] = "open" if (rest and not stop) else ("win" if res["split_pnl"] > 0 else "loss")
    res["risk"] = d * (entry - sl)
    return res


def summary(results: dict, rule: str) -> str:
    pnl = [r[f"{rule}_pnl"] for r in results.values() if r.get("status") == "closed" and r[f"{rule}_res"] != "open"]
    wins = [p for p in pnl if p > 0]
    losses = [p for p in pnl if p <= 0]
    n_open = sum(1 for r in results.values() if r.get("status") == "closed" and r[f"{rule}_res"] == "open")
    pf = sum(wins) / -sum(losses) if losses and sum(losses) < 0 else float("inf")
    wr = len(wins) / len(pnl) if pnl else float("nan")
    return (f"closed {len(pnl)}, wins {len(wins)}, losses {len(losses)}, win rate {100 * wr:.0f}%, "
            f"profit factor {pf:.2f}, net {sum(pnl):+.2f} $/oz" + (f" (+{n_open} still open)" if n_open else ""))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("signals")
    ap.add_argument("--moves", default=None, help="stop-move CSV (default: <signals>_stop_moves.csv if present)")
    ap.add_argument("--end", default=None, help="UTC data end (default: now)")
    a = ap.parse_args()
    sigs = pd.read_csv(a.signals)
    mpath = a.moves or a.signals.replace(".csv", "_stop_moves.csv")
    moves = pd.read_csv(mpath) if os.path.exists(mpath) else pd.DataFrame(columns=["posted_local", "utc_offset_h", "applies_to", "new_sl"])
    end = pd.Timestamp(a.end, tz="UTC") if a.end else pd.Timestamp.now(tz="UTC").floor("h")
    first = (pd.to_datetime(sigs["posted_local"]) - pd.to_timedelta(sigs["utc_offset_h"], unit="h")).min().tz_localize("UTC")
    bid, ask = load_candles(sigs["symbol"].iloc[0], first - pd.Timedelta(hours=1), end)
    print(f"prices: Dukascopy {sigs['symbol'].iloc[0]} BID/ASK 1m, {bid.index.min()} -> {bid.index.max()} "
          f"({len(bid)} minutes with trades); median spread {float((ask['close'] - bid['close']).median()):.2f}")
    for label, as_stated in (("FOLLOWER (fill at the next minute's price, spread paid)", False),
                             ("AS HE STATES IT (fill at his entry price)", True)):
        res = {}
        print(f"\n=== {label} ===")
        for _, s in sigs.iterrows():
            r = replay(s, moves, bid, ask, as_stated)
            res[s["id"]] = r
            if r["status"] != "closed":
                print(f"  {s['id']} {s['side']:4s} {s['order']:6s} {s['entry']}: {r['status']}")
                continue
            h = ", ".join(f"{k.upper()} {v:%m-%d %H:%M}" for k, v in r["hits"].items()) or "no target"
            st = f"STOP {r['stop_at'][1]:.0f} at {r['stop_at'][0]:%m-%d %H:%M}" if r["stop_at"] else "stop not hit"
            print(f"  {s['id']} {s['side']:4s} {s['order']:6s} fill {r['entry']:.2f} at {r['fill']:%m-%d %H:%M} UTC "
                  f"(risk {r['risk']:.1f}): {h}; {st}  ->  TP1 rule {r['tp1_pnl']:+6.2f} [{r['tp1_res']}]  "
                  f"TP4 rule {r['tp4_pnl']:+6.2f} [{r['tp4_res']}]  split {r['split_pnl']:+6.2f} [{r['split_res']}]")
        for rule, name in (("tp1", "TP1 or stop"), ("tp4", "TP4 or stop"), ("split", "quarter at each TP")):
            print(f"  {name:20s}: {summary(res, rule)}")


if __name__ == "__main__":
    main()
