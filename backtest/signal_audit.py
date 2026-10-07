"""
Audit a Telegram signal channel against real prices: what would a follower actually have made?

Two inputs:
- a CSV of signals read from screenshots (id, posted_local, utc_offset_h, symbol, side, order, entry,
  tp1..tp4, sl) with an optional <name>_stop_moves.csv; or
- --channel <messages.csv> from backtest/fetch_tg_channel.py: every setup, stop move and close
  instruction is parsed from the channel's own posts (rules in parse_channel()).

Prices: Dukascopy BID and ASK 1-minute candles (complete UTC days) plus hourly ticks for the current
day. Buys fill at the ASK and exit at the BID, sells the reverse, so the spread is always paid.

Replay rules (fixed before any result was read):
- market signal: fills at the open of the first minute after the post; "as stated": his entry price.
- limit/stop orders: fill when traded at/through the price after the post (gapped opens fill at the
  open); unfilled after 24 hours = cancelled.
- stop first when a minute touches both; targets need a trade through them and never fill on the
  fill minute; instructions apply from the first minute after they were posted.
- a price-level stop move is applied only if the broker would accept it (below the bid for a buy,
  above the ask for a sell); "entry"/"breakeven" moves the stop to the follower's own fill price.
- a close instruction exits whatever is left at the next minute's open.
Three ways to manage the four targets: all out at TP1 (how channels count wins), all out at TP4,
a quarter at each target. Anything still open at the data end is marked to market (listed as open).

  python3 backtest/signal_audit.py backtest/signal_audits/tsa_free_trades.csv
  python3 backtest/fetch_tg_channel.py tradesmartacademy --out backtest/data_cache/local/tg/tradesmartacademy_messages.csv
  python3 backtest/signal_audit.py --channel backtest/data_cache/local/tg/tradesmartacademy_messages.csv [--spread 0.30]
"""

import argparse
import lzma
import os
import re
import struct
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, ".")
import backtest.fetch_dukascopy as fd  # noqa: E402

RAW = "backtest/data_cache/local/duka_raw_gold"
TICK = struct.Struct(">IIIff")          # ms offset, ask, bid, ask volume, bid volume
SCALE = 1000.0                          # XAUUSD points (0.001)
PENDING_EXPIRY = pd.Timedelta(hours=24)
MGMT_WINDOW = pd.Timedelta(hours=48)    # instructions apply to signals posted within this window
MAX_FILL_DELAY = pd.Timedelta(minutes=60)  # a market signal with no price within this is "market closed"
BE_EPS = 0.01
DUP_WINDOW = pd.Timedelta(hours=24)


# ----------------------------------------------------------------------------------------------
# prices
# ----------------------------------------------------------------------------------------------
def load_candles(symbol: str, start: pd.Timestamp, end: pd.Timestamp) -> tuple:
    os.makedirs(RAW, exist_ok=True)
    bids, asks = [], []
    for day in pd.date_range(start.normalize().tz_localize(None), end.tz_localize(None), freq="D"):
        if day.weekday() == 5:
            continue
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
    bid = bid[~bid.index.duplicated()]
    ask = ask[~ask.index.duplicated()]
    keep = bid["volume"] > 0                      # Dukascopy pads closed hours with flat bars
    bid = bid[keep]
    ask = ask.reindex(bid.index)
    return bid, ask


HISTDATA_GOLD = "backtest/data_cache/local/xauusd_histdata_1m_2015_2026.csv.gz"
HISTDATA_END = pd.Timestamp("2026-10-01", tz="UTC")


def load_prices(start: pd.Timestamp, end: pd.Timestamp, spread) -> tuple:
    """Gold BID/ASK minutes for a long audit without hammering Dukascopy's throttled feed.
    BID: HistData M1 up to 30 Sep 2026 (it IS Dukascopy's BID: 99.97% of 71,788 overlapping minutes
    identical), Dukascopy candles/ticks after that. ASK: with spread="duka", Dukascopy's own ASK on
    days already cached and BID + Dukascopy's median spread for that UTC hour elsewhere; with a
    number, BID + that fixed spread (e.g. 0.30 for a tight ECN account)."""
    import glob
    from backtest.data import load_cached_1m
    h = load_cached_1m(HISTDATA_GOLD)
    h.index = h.index.tz_convert("UTC")
    h = h[(h.index >= start) & (h.index < min(end, HISTDATA_END))]
    parts = [h]
    if end > HISTDATA_END:
        db, _ = load_candles("XAUUSD", HISTDATA_END, end)
        parts.append(db[db.index >= HISTDATA_END])
    bid = pd.concat(parts).sort_index()
    bid = bid[~bid.index.duplicated()]
    if spread != "duka":
        ask = bid.copy()
        ask[["open", "high", "low", "close"]] += float(spread)
        return bid, ask
    cached = [pd.read_pickle(f) for f in sorted(glob.glob(f"{RAW}/XAUUSD_*_ASK.pkl"))]
    real = pd.concat([c.set_index("timestamp") for c in cached if len(c)]).sort_index()
    real = real[~real.index.duplicated()]
    _, ta = load_candles("XAUUSD", max(start, HISTDATA_END), end) if end > HISTDATA_END else (None, None)
    if ta is not None:
        real = pd.concat([real, ta]).sort_index()
        real = real[~real.index.duplicated()]
    rb = bid.reindex(real.index)
    prof = (real["close"] - rb["close"]).dropna()
    prof = prof.groupby(prof.index.hour).median()
    model = bid.copy()
    add = np.asarray(prof.reindex(bid.index.hour).to_numpy())
    for c in ("open", "high", "low", "close"):
        model[c] = bid[c].to_numpy() + add
    ask = model
    have = bid.index.intersection(real.index)
    ask.loc[have, ["open", "high", "low", "close"]] = real.loc[have, ["open", "high", "low", "close"]].to_numpy()
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


# ----------------------------------------------------------------------------------------------
# replay
# ----------------------------------------------------------------------------------------------
def replay(sig: dict, events: list, bid: pd.DataFrame, ask: pd.DataFrame, as_stated: bool) -> dict:
    """sig: id, post (UTC), side (buy/sell), order (market/limit/stop), entry, tps[4], sl.
    events: [(utc, "sl", price | "entry") | (utc, "close", None)] in time order."""
    d = 1 if sig["side"] == "buy" else -1
    tps, sl0, post = sig["tps"], float(sig["sl"]), sig["post"]
    ent_px, ex_px = (ask, bid) if d == 1 else (bid, ask)
    after = ent_px.index >= post.floor("min") + pd.Timedelta(minutes=1)
    if not after.any():
        return {"status": "no data"}
    if sig["order"] == "market":
        i0 = int(np.argmax(after))
        fill_t = ent_px.index[i0]
        if fill_t - post > MAX_FILL_DELAY:
            return {"status": "market closed at post", "post": post}
        entry = float(sig["entry"]) if as_stated else float(ent_px["open"].iloc[i0])
        if d * (tps[0] - entry) <= 0:
            return {"status": "stale: price already past TP1", "post": post}
    else:
        lvl = float(sig["entry"])
        e = ent_px[after & (ent_px.index <= post + PENDING_EXPIRY)]
        below = (sig["order"] == "limit") == (d == 1)          # buy limit / sell stop fill on the way down
        hit = (e["low"] <= lvl) if below else (e["high"] >= lvl)
        if not hit.any():
            return {"status": "never filled", "post": post}
        fill_t = hit.idxmax()
        o = float(e.loc[fill_t, "open"])
        entry = (min(o, lvl) if below else max(o, lvl))
    x = ex_px[ex_px.index >= fill_t]
    sl, hits, end = sl0, {}, None
    for et, kind, val in events:                       # price-level stop moves made while the order was pending
        if et < fill_t and kind == "sl" and val != "entry" and d * (entry - float(val)) > 0:
            sl = float(val)
    ev = [e for e in events if e[0] >= fill_t - pd.Timedelta(minutes=1)]
    k_ev = 0
    prev_close = float(x["open"].iloc[0])
    for t, row in x.iterrows():
        while k_ev < len(ev) and ev[k_ev][0] < t:
            et, kind, val = ev[k_ev]
            k_ev += 1
            if kind == "sl":
                new = entry if val == "entry" else float(val)
                if (d == 1 and new < prev_close) or (d == -1 and new > prev_close):
                    sl = new
            elif kind == "close" and t > fill_t:
                end = (t, float(row["open"]), "closed by him")
                break
        if end:
            break
        if (row["low"] <= sl) if d == 1 else (row["high"] >= sl):
            gap = (row["open"] <= sl) if d == 1 else (row["open"] >= sl)
            end = (t, float(row["open"]) if gap else sl, "stop")
            break
        if t > fill_t:
            for k, tp in enumerate(tps, 1):
                if f"tp{k}" not in hits and ((row["high"] > tp) if d == 1 else (row["low"] < tp)):
                    hits[f"tp{k}"] = t
        if len(hits) == 4:
            break
        prev_close = float(row["close"])
    last = float(x["close"].iloc[-1])
    pts = lambda px: d * (px - entry)
    res = {"status": "filled", "post": post, "fill": fill_t, "entry": entry, "hits": hits, "end": end,
           "sl_final": sl, "risk": d * (entry - sl0), "mark": last}
    label = lambda p: "win" if p > BE_EPS else ("loss" if p < -BE_EPS else "breakeven")
    for rule, k in (("tp1", 1), ("tp4", 4)):
        if f"tp{k}" in hits:
            p = pts(tps[k - 1])
        elif end:
            p = pts(end[1])
        else:
            res[f"{rule}_pnl"], res[f"{rule}_res"] = pts(last), "open"
            continue
        res[f"{rule}_pnl"], res[f"{rule}_res"] = p, label(p)
    got = [pts(tps[k - 1]) for k in range(1, 5) if f"tp{k}" in hits]
    rest = 4 - len(got)
    tail = pts(end[1]) if end else pts(last)
    res["split_pnl"] = (sum(got) + rest * tail) / 4.0
    res["split_res"] = "open" if (rest and not end) else label(res["split_pnl"])
    return res


def stats(results: list, rule: str) -> dict:
    done = [r for r in results if r.get("status") == "filled" and r[f"{rule}_res"] != "open"]
    pnl = np.array([r[f"{rule}_pnl"] for r in done])
    risk = np.array([r["risk"] for r in done])
    wins, losses = pnl[pnl > BE_EPS], pnl[pnl < -BE_EPS]
    return {"n": len(pnl), "wins": len(wins), "losses": len(losses), "be": int(len(pnl) - len(wins) - len(losses)),
            "wr": len(wins) / len(pnl) if len(pnl) else np.nan,
            "pf": wins.sum() / -losses.sum() if losses.sum() < 0 else np.inf,
            "net": pnl.sum(), "net_R": float((pnl / risk).sum()) if len(pnl) else 0.0,
            "open": sum(1 for r in results if r.get("status") == "filled" and r[f"{rule}_res"] == "open")}


def fmt(s: dict) -> str:
    return (f"closed {s['n']:3d}, wins {s['wins']:3d}, losses {s['losses']:3d}, breakeven {s['be']:3d}, win rate {100 * s['wr']:4.0f}%, "
            f"PF {s['pf']:5.2f}, net {s['net']:+8.1f} $/oz ({s['net_R']:+6.1f} R)"
            + (f", +{s['open']} open" if s["open"] else ""))


# ----------------------------------------------------------------------------------------------
# channel parsing
# ----------------------------------------------------------------------------------------------
SETUP = re.compile(r"potential market setup:\s*([a-z]{3}/?[a-z]{3}|[a-z0-9]+)\s*-\s*(buy|sell)\s*(limit|stop)?", re.I)
NUM = r"([0-9]+(?:\.[0-9]+)?)"
MOVE = re.compile(r"\bmove\b[^\n]*?\b(?:sl|s/l|stop\s*loss(?:es)?|stoploss(?:es)?|stops?)\b[^\n]*?\bto\s+(?:your\s+|the\s+)?"
                  r"(entry|break\s*even|be\b|" + NUM + ")", re.I)
CLOSE = re.compile(r"\bclose\s+(?:all\b|it\b|at\s+\d|now\b|everything\b|half\b|tp\s*\d|(?:the|your)\s+(?:gold|trades?|positions?|buys?|sells?)\b"
                   r"|gold\b|buys\b|sells\b|positions?\b|trades?\b)", re.I)


def parse_channel(msgs: pd.DataFrame) -> tuple:
    """-> (signals, instructions, counts). Setups need an entry, TP1-TP4 and a stop; an identical
    setup re-posted within 24 hours is the same signal."""
    msgs = msgs.copy()
    msgs["utc"] = pd.to_datetime(msgs["utc"], utc=True)
    msgs["text"] = msgs["text"].fillna("")
    sigs, instr, counts = [], [], {"setups_seen": 0, "unparsed_setups": 0, "duplicates": 0, "non_gold": 0}
    for _, m in msgs.sort_values("id").iterrows():
        t = m["text"]
        sm = SETUP.search(t)
        if sm:
            counts["setups_seen"] += 1
            sym = sm.group(1).upper().replace("/", "")
            if sym != "XAUUSD":
                counts["non_gold"] += 1
                continue
            side = sm.group(2).lower()
            ent = re.search(r"entry\s*price:\s*" + NUM, t, re.I)
            zone = re.search(r"entry\s*zone:\s*" + NUM + r"\s*[-–—]\s*" + NUM, t, re.I)
            tps = [re.search(rf"tp\s*{k}\s*:\s*" + NUM, t, re.I) for k in range(1, 5)]
            slm = re.search(r"stop\s*loss\s*\(sl\)\s*:\s*" + NUM, t, re.I)
            got = [float(x.group(1)) for x in tps if x]
            if (not ent and not zone) or not slm or not tps[0]:
                counts["unparsed_setups"] += 1
                continue
            if ent:
                entry = float(ent.group(1))
            else:                                          # a zone: the edge price reaches first
                a_, b_ = float(zone.group(1)), float(zone.group(2))
                entry = max(a_, b_) if side == "buy" else min(a_, b_)
            got += [got[-1]] * (4 - len(got))              # fewer than four targets: the last one repeats
            s = {"id": int(m["id"]), "post": m["utc"], "side": side,
                 "order": (sm.group(3) or "market").lower(), "entry": entry, "tps": got, "sl": float(slm.group(1))}
            s["garbled"] = bool(abs(s["entry"] - s["sl"]) > 80 or
                                (side == "buy" and (s["sl"] >= s["entry"] or got[0] <= s["entry"])) or
                                (side == "sell" and (s["sl"] <= s["entry"] or got[0] >= s["entry"])))
            key = (s["side"], s["order"], s["entry"], s["sl"], s["tps"][0])
            if any((p["side"], p["order"], p["entry"], p["sl"], p["tps"][0]) == key and s["post"] - p["post"] <= DUP_WINDOW
                   for p in sigs[-10:]):
                counts["duplicates"] += 1
                continue
            sigs.append(s)
            continue
        mv = MOVE.search(t)
        if mv:
            val = mv.group(1).lower()
            instr.append((m["utc"], "sl", "entry" if not val[0].isdigit() else float(val), t[:80], int(m["id"])))
        if CLOSE.search(t):
            side = "buy" if re.search(r"\bbuys?\b", t, re.I) else ("sell" if re.search(r"\bsells?\b", t, re.I) else None)
            instr.append((m["utc"], "close", side, t[:80], int(m["id"])))
    return sigs, instr, counts


def events_for(sig: dict, instr: list) -> list:
    ev = []
    for (t, kind, val, _txt, _id) in instr:
        if not (sig["post"] < t <= sig["post"] + MGMT_WINDOW):
            continue
        if kind == "close" and val not in (None, sig["side"]):
            continue
        ev.append((t, kind, val))
    return ev


def claimed_results(msgs: pd.DataFrame) -> dict:
    tot = {"posts": 0, "trades": 0, "winners": 0, "losses": 0}
    for t in msgs["text"].fillna(""):
        m = re.search(r"(\d+)\s*trades?\s*shared.*?(\d+)\s*winners?.*?(\d+)\s*loss", t, re.I | re.S)
        if m:
            tot["posts"] += 1
            tot["trades"] += int(m.group(1))
            tot["winners"] += int(m.group(2))
            tot["losses"] += int(m.group(3))
    return tot


# ----------------------------------------------------------------------------------------------
# entry points
# ----------------------------------------------------------------------------------------------
def run_csv(path: str, moves_path: str | None, end: pd.Timestamp) -> None:
    sigs = pd.read_csv(path)
    mpath = moves_path or path.replace(".csv", "_stop_moves.csv")
    moves = pd.read_csv(mpath) if os.path.exists(mpath) else pd.DataFrame(columns=["posted_local", "utc_offset_h", "applies_to", "new_sl"])
    to_utc = lambda loc, off: (pd.Timestamp(loc) - pd.Timedelta(hours=float(off))).tz_localize("UTC")
    first = min(to_utc(r["posted_local"], r["utc_offset_h"]) for _, r in sigs.iterrows())
    bid, ask = load_candles(sigs["symbol"].iloc[0], first - pd.Timedelta(hours=1), end)
    print(f"prices: Dukascopy BID/ASK 1m {bid.index.min()} -> {bid.index.max()}; median spread "
          f"{float((ask['close'] - bid['close']).median()):.2f}")
    for label, as_stated in (("FOLLOWER (next minute's price, spread paid)", False), ("AS HE STATES IT (his entry price)", True)):
        print(f"\n=== {label} ===")
        res = []
        for _, s in sigs.iterrows():
            sig = {"id": s["id"], "post": to_utc(s["posted_local"], s["utc_offset_h"]), "side": s["side"],
                   "order": s["order"], "entry": s["entry"], "tps": [float(s[f"tp{k}"]) for k in range(1, 5)], "sl": s["sl"]}
            ev = sorted([(to_utc(r["posted_local"], r["utc_offset_h"]), "sl", float(r["new_sl"]))
                         for _, r in moves.iterrows() if s["id"] in str(r["applies_to"]).split("|")])
            r = replay(sig, ev, bid, ask, as_stated)
            res.append(r)
            print("  " + line(s["id"], sig, r))
        for rule, name in (("tp1", "all out at TP1"), ("tp4", "all out at TP4"), ("split", "quarter at each TP")):
            print(f"  {name:20s}: {fmt(stats(res, rule))}")


def line(sid, sig: dict, r: dict) -> str:
    head = f"{sid} {sig['post']:%Y-%m-%d %H:%M} {sig['side']:4s} {sig['order']:6s} {sig['entry']:.1f} sl {sig['sl']:.0f}"
    if r.get("status") != "filled":
        return f"{head}: {r.get('status')}"
    h = ",".join(k.upper() for k in r["hits"]) or "no TP"
    e = f"{r['end'][2]} {r['end'][1]:.2f}" if r["end"] else ("all 4 TPs" if len(r["hits"]) == 4 else "still open")
    return (f"{head} fill {r['entry']:.2f}: {h}; {e} -> TP1 {r['tp1_pnl']:+6.2f} [{r['tp1_res']}] "
            f"TP4 {r['tp4_pnl']:+6.2f} [{r['tp4_res']}] split {r['split_pnl']:+6.2f}")


def run_channel(path: str, end: pd.Timestamp, since: str | None, detail: bool, spread="duka") -> None:
    msgs = pd.read_csv(path)
    sigs, instr, counts = parse_channel(msgs)
    if since:
        sigs = [s for s in sigs if s["post"] >= pd.Timestamp(since, tz="UTC")]
    print(f"{path}: {len(msgs)} messages; setups seen {counts['setups_seen']}, gold signals {len(sigs)} "
          f"(duplicates dropped {counts['duplicates']}, unparsed {counts['unparsed_setups']}, other symbols {counts['non_gold']}); "
          f"instructions: {sum(1 for i in instr if i[1] == 'sl')} stop moves, {sum(1 for i in instr if i[1] == 'close')} closes")
    garbled = [s for s in sigs if s.get("garbled")]
    sigs = [s for s in sigs if not s.get("garbled")]
    print(f"garbled signals set aside (stop on the wrong side or > $80 away): {len(garbled)} "
          f"(ids {', '.join(str(g['id']) for g in garbled)})")
    bid, ask = load_prices(min(s["post"] for s in sigs) - pd.Timedelta(hours=1), end, spread)
    print(f"prices: XAUUSD BID/ASK 1m {bid.index.min():%Y-%m-%d} -> {bid.index.max():%Y-%m-%d %H:%M}; "
          f"spread {'Dukascopy (real where cached, hourly median elsewhere)' if spread == 'duka' else f'fixed {spread}'}, "
          f"median {float((ask['close'] - bid['close']).median()):.2f}")
    claim = claimed_results(msgs)
    for label, as_stated in (("FOLLOWER (next minute's price, spread paid)", False), ("AS HE STATES IT (his entry price)", True)):
        res = []
        for s in sigs:
            r = replay(s, events_for(s, instr), bid, ask, as_stated)
            r["month"] = s["post"].strftime("%Y-%m")
            r["side"] = s["side"]
            res.append(r)
            if detail and not as_stated:
                print("  " + line(s["id"], s, r))
        print(f"\n=== {label} ===")
        nf = sum(1 for r in res if r.get("status") == "never filled")
        print(f"  signals {len(res)}, pending orders never filled {nf}")
        for rule, name in (("tp1", "all out at TP1"), ("tp4", "all out at TP4"), ("split", "quarter at each TP")):
            print(f"  {name:20s}: {fmt(stats(res, rule))}")
        if not as_stated:
            print("  by month (all out at TP1 | quarter at each TP):")
            for mo in sorted({r["month"] for r in res}):
                sub = [r for r in res if r["month"] == mo]
                a, b = stats(sub, "tp1"), stats(sub, "split")
                print(f"    {mo}: n {a['n']:3d}  TP1 win {100 * a['wr']:4.0f}% PF {a['pf']:5.2f} net {a['net']:+7.1f} | "
                      f"split PF {b['pf']:5.2f} net {b['net']:+7.1f}")
            for side in ("buy", "sell"):
                sub = [r for r in res if r["side"] == side]
                print(f"  {side}s: TP1 {fmt(stats(sub, 'tp1'))}")
            fin = [r for r in res if r.get("status") == "filled"]
            tp1 = np.mean([("tp1" in r["hits"]) for r in fin])
            avg_t1 = np.mean([abs(s["tps"][0] - s["entry"]) for s in sigs])
            avg_sl = np.mean([abs(s["entry"] - s["sl"]) for s in sigs])
            print(f"  average TP1 distance ${avg_t1:.1f}, stop distance ${avg_sl:.1f}: TP1 must hit "
                  f"{100 * avg_sl / (avg_sl + avg_t1):.0f}% of the time to break even before costs; it hit {100 * tp1:.0f}%")
    if claim["posts"]:
        print(f"\nhis own 'VIP RESULTS' posts ({claim['posts']}): {claim['trades']} trades, {claim['winners']} winners, "
              f"{claim['losses']} losses = {100 * claim['winners'] / max(claim['trades'], 1):.0f}% claimed win rate (VIP trades are not visible)")


def selftest() -> None:
    fails = 0

    def check(name: str, ok: bool) -> None:
        nonlocal fails
        fails += 0 if ok else 1
        print(f"{'PASS' if ok else 'FAIL'}  {name}")

    closes = {"Close all gold buys\nOPEN NEW GOLD SELLS": True, "Close the gold buys here with a loss.": True,
              "Close it with a small loss here.": True, "Accept the - 40 pips loss here and close at 4174.": True,
              "CLOSE TP2 +220 Pips": True, "Nah. Nobody comes close.": False, "Let's close the week strong": False,
              "close to 4200 now": False}
    check("close instructions parsed, chatter ignored", all(bool(CLOSE.search(t)) == w for t, w in closes.items()))
    moves = {"Move SL to your entry now": "entry", "Move all gold stoplosses to 4380": "4380",
             "Move stoploss one last time to 4390.": "4390", "MOVE GOLd STOPLOSS TO 4335\nONE LAST TIME": "4335",
             "Move SL to 4360 be ready for counter trade.": "4360", "Gold will move to 4200 soon": None}
    check("stop moves parsed (price or entry), chatter ignored",
          all(((m := MOVE.search(t)) and m.group(1).lower()) == w or (m is None and w is None) for t, w in moves.items()))
    idx = pd.date_range("2026-01-05 10:00", periods=8, freq="1min", tz="UTC")
    mk = lambda o, h, low, c: pd.DataFrame({"open": o, "high": h, "low": low, "close": c, "volume": 1.0}, index=idx)
    bid = mk([100.0] * 8, [100, 100, 105, 100, 100, 100, 100, 100], [100, 100, 100, 100, 89, 100, 100, 100], [100.0] * 8)
    ask = bid + 0.5
    sig = {"id": 1, "post": idx[0], "side": "buy", "order": "market", "entry": 100.0, "tps": [104, 106, 108, 110], "sl": 90.0}
    r = replay(sig, [], bid, ask, as_stated=False)
    check("buy fills at the next minute's ASK; TP1 then the stop: TP1 rule wins, TP4 rule loses",
          r["entry"] == 100.5 and r["tp1_res"] == "win" and abs(r["tp1_pnl"] - 3.5) < 1e-9
          and r["tp4_res"] == "loss" and abs(r["tp4_pnl"] + 10.5) < 1e-9)
    r = replay(sig, [(idx[2] + pd.Timedelta(seconds=30), "close", None)], bid, ask, as_stated=False)
    check("a close instruction exits at the next minute's open", r["end"] is not None and r["end"][0] == idx[3]
          and r["end"][2] == "closed by him")
    r = replay(sig, [(idx[1] + pd.Timedelta(seconds=5), "sl", 101.0)], bid, ask, as_stated=False)
    check("a stop move above the bid is rejected (the broker would refuse it)", r["sl_final"] == 90.0)
    print(f"\nselftest: {'ALL PASS' if fails == 0 else f'{fails} FAILED'}")
    if fails:
        sys.exit(1)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("signals", nargs="?")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--channel", default=None, help="messages CSV from fetch_tg_channel.py")
    ap.add_argument("--moves", default=None)
    ap.add_argument("--since", default=None)
    ap.add_argument("--detail", action="store_true")
    ap.add_argument("--end", default=None, help="UTC data end (default: now)")
    ap.add_argument("--spread", default="duka", help="'duka' or a fixed spread in $ (e.g. 0.30)")
    a = ap.parse_args()
    end = pd.Timestamp(a.end, tz="UTC") if a.end else pd.Timestamp.now(tz="UTC").floor("h")
    if a.selftest:
        selftest()
        return
    if a.channel:
        run_channel(a.channel, end, a.since, a.detail, a.spread if a.spread == "duka" else float(a.spread))
    else:
        run_csv(a.signals, a.moves, end)


if __name__ == "__main__":
    main()
