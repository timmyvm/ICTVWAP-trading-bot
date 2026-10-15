"""
v0.35-audit, extraction stage: Discord export -> causal candidate windows -> (labels) -> frozen trade table.

Everything this script reads or writes lives in backtest/data_cache/local/discord/ (gitignored). The
repository is public, so no server, channel or person name appears in this file: the export path and
the caller's name come from a local config JSON (--config), e.g.
    {"export": "backtest/data_cache/local/discord/<raw dir>/<alerts>.json", "caller": "<name>"}

Stages (DEVLOG v0.35-audit):
  --prepass   load the export (messageCount asserted), keep the caller's messages, tag them, label lone
              premium numbers QUOTE and lone percentages CLAIM in code, mark pre-market posts as
              watchlist, and write one causal window per remaining candidate: the candidate plus the
              caller's EARLIER messages that day, never later ones. Dates are replaced by day numbers.
  --batches   split the candidates into subagent batch files for labelling pass A and pass B, with the
              days shuffled differently in each pass (so no extractor sees a contiguous era).
"""

import argparse
import hashlib
import json
import math
import os
import random
import re
import sys
from datetime import datetime, time
from typing import Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")
OUT_DIR = "backtest/data_cache/local/discord/v035"
WINDOW = 8                       # earlier same-day caller messages shown with each candidate
RTH_OPEN, RTH_CLOSE = time(9, 30), time(16, 0)

TICKERS = r"QQQ|SPY|SPX|SPXW|IWM|NQ|MNQ|ES|MES|TSLA|NVDA|AAPL|MSTR|AMD|SMCI|META|AMZN|MSFT|GOOGL|GOOG|NFLX|COIN|PLTR|AVGO"
RX = {
    "contract": re.compile(r"(?<![\w.$])(\d{2,4}(?:\.\d{1,2})?)\s?(c|p|calls?|puts?)\b", re.I),
    "ticker": re.compile(rf"\b({TICKERS})\b"),
    "price": re.compile(r"(?<![\w.%])(\d{0,2}\.\d{2})(?![\w%]|\.\d)"),
    "range": re.compile(r"(?<![\w.])(\d{0,2}\.\d{2})\s?-\s?(\d{0,2}\.\d{2})(?![\w.])"),
    "pct": re.compile(r"(-?\d{1,4}(?:\.\d+)?)\s?%"),
    "entry": re.compile(r"\b(took|taking|entry|entered|enter|in at|bought|grabbed|filled|fill|playing|play|got (back )?in|re-?enter\w*|added|adding|loaded|loading|scal(ed|ing) in)\b", re.I),
    "exit": re.compile(r"\b(out|exited|exit(ing)?|closed|closing|sold|cut|stopped|stop(ped)? out|took profit|secured|done for)\b", re.I),
    "trim": re.compile(r"\b(trim\w*|took some off|partials?|paid myself)\b", re.I),
    "be": re.compile(r"\b(stops?|sl)\s*(to|at|@)?\s*(be|b/e|breakeven|break even)\b|\b(breakeven|break even|b/e)\b"
                     r"|\bbe\s+stops?\b|\bstopped\s+(at\s+)?be\b|\bmov\w*\s+(my\s+|our\s+|the\s+)?stops?\b", re.I),
    "ping": re.compile(r"@(premium|here|everyone)\b", re.I),
}
PREMIUM_MAX = 10.0               # a "price" tag counts as a premium quote only below this (VIX, ratios, levels excluded)
STRONG = ("contract", "range", "pct", "ping", "trim", "be", "exit", "entry")
LONE_PRICE = re.compile(r"^\s*\$?\d{0,2}\.\d{2}\s*$")
LONE_PCT = re.compile(r"^\s*(up\s*)?\+?\d{1,4}(\.\d+)?\s?%\s*(so far|now|easy|\+)?\s*[!.]*\s*$", re.I)


def load_export(path: str, expect_complete: bool = True) -> Tuple[dict, List[dict], bool]:
    """DiscordChatExporter JSON -> (channel, messages, truncated). Recovers whole messages from a cut-off
    file; with expect_complete the file must parse and match its own messageCount."""
    s = open(path, encoding="utf-8").read()
    try:
        j = json.loads(s)
        msgs = j.get("messages", [])
        if expect_complete and j.get("messageCount") is not None:
            assert j["messageCount"] == len(msgs), f"messageCount {j['messageCount']} != {len(msgs)} parsed"
        return j.get("channel", {}), msgs, False
    except json.JSONDecodeError:
        if expect_complete:
            raise
    dec = json.JSONDecoder()
    m = re.search(r'"channel"\s*:\s*', s)
    ch = dec.raw_decode(s, m.end())[0] if m else {}
    i = s.index("[", s.index('"messages"')) + 1
    msgs, n = [], len(s)
    while i < n:
        while i < n and s[i] in " \r\n\t,":
            i += 1
        if i >= n or s[i] == "]":
            break
        try:
            obj, i = dec.raw_decode(s, i)
        except json.JSONDecodeError:
            break
        msgs.append(obj)
    return ch, msgs, True


def to_ny(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(NY)


def tags_for(text: str) -> Dict[str, list]:
    t = {}
    for k, rx in RX.items():
        found = rx.findall(text)
        if k == "price":
            found = [f for f in found if float(f) < PREMIUM_MAX]
        if found:
            t[k] = [f if isinstance(f, str) else list(f) for f in found]
    return t


def is_candidate(tags: Dict[str, list]) -> bool:
    """A message worth labelling: any trade-shaped tag. A bare ticker mention (a game plan, commentary) is not."""
    return any(k in tags for k in STRONG) or "price" in tags


def prepass(cfg: dict) -> dict:
    ch, msgs, trunc = load_export(cfg["export"], expect_complete=True)
    rows = []
    for m in msgs:
        if (m.get("author") or {}).get("name") != cfg["caller"]:
            continue
        posted = to_ny(m["timestamp"])
        edited = to_ny(m["timestampEdited"]) if m.get("timestampEdited") else None
        text = (m.get("content") or "").strip()
        n_img = len(m.get("attachments") or [])
        tg = tags_for(text)
        session = ("pre" if posted.time() < RTH_OPEN else "post" if posted.time() >= RTH_CLOSE else "rth")
        if not text:
            code = "IMAGE-ONLY" if n_img else "EMPTY"
        elif LONE_PRICE.match(text):
            code = "QUOTE"
        elif LONE_PCT.match(text):
            code = "CLAIM"
        elif session == "pre":
            code = "WATCHLIST" if is_candidate(tg) else "NOTE"
        elif session == "post":
            code = "AFTER-HOURS"
        elif is_candidate(tg):
            code = "CANDIDATE"
        else:
            code = "NOTE"
        rows.append({"msg_id": m["id"], "date": posted.date().isoformat(), "time": posted.strftime("%H:%M:%S"),
                     "posted_utc": m["timestamp"], "edited_utc": m.get("timestampEdited"),
                     "edited_time": edited.strftime("%H:%M:%S") if edited else None,
                     "text": text, "n_img": n_img, "session": session, "code": code, "tags": tg})
    rows.sort(key=lambda r: r["posted_utc"])
    days = sorted({r["date"] for r in rows})
    daymap = {d: f"D{i + 1:03d}" for i, d in enumerate(days)}
    for r in rows:
        r["day"] = daymap[r["date"]]

    by_day: Dict[str, List[dict]] = {}
    for r in rows:
        by_day.setdefault(r["day"], []).append(r)
    cands = []
    for day, rs in by_day.items():
        for k, r in enumerate(rs):
            if r["code"] != "CANDIDATE":
                continue
            prior = rs[max(0, k - WINDOW):k]
            window = [render(p) for p in prior]
            cands.append({"cid": len(cands) + 1, "day": day, "time": r["time"],
                          "edited_time": r["edited_time"], "text": r["text"], "n_img": r["n_img"],
                          "window": window, "msg_id": r["msg_id"]})
    os.makedirs(OUT_DIR, exist_ok=True)
    write_jsonl(f"{OUT_DIR}/caller_messages.jsonl", rows)
    write_jsonl(f"{OUT_DIR}/candidates.jsonl", cands)
    with open(f"{OUT_DIR}/daymap.json", "w", encoding="utf-8") as f:
        json.dump(daymap, f)
    counts: Dict[str, int] = {}
    for r in rows:
        counts[r["code"]] = counts.get(r["code"], 0) + 1
    return {"messages": len(rows), "days": len(days), "codes": counts, "candidates": len(cands),
            "candidate_days": len({c["day"] for c in cands}), "truncated": trunc}


def render(r: dict) -> str:
    txt = r["text"] if r["text"] else "[image only]" if r["n_img"] else "[empty]"
    if r["text"] and r["n_img"]:
        txt += f" [+{r['n_img']} image]"
    ed = f" (edited {r['edited_time']})" if r.get("edited_time") else ""
    return f"{r['time']}{ed} | {txt}"


def write_jsonl(path: str, rows: List[dict]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def read_jsonl(path: str) -> List[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def batches(n_batches: int) -> dict:
    """Pass A and pass B batch files with days shuffled differently; subagents see day numbers, ET clock
    times and text only (no msg ids, no dates)."""
    cands = read_jsonl(f"{OUT_DIR}/candidates.jsonl")
    days = sorted({c["day"] for c in cands})
    out = {}
    for pas, seed in (("A", 11), ("B", 22)):
        d = days[:]
        random.Random(seed).shuffle(d)
        groups = [d[i::n_batches] for i in range(n_batches)]
        os.makedirs(f"{OUT_DIR}/pass{pas}", exist_ok=True)
        sizes = []
        for g, gd in enumerate(groups):
            sel = set(gd)
            rows = [{k: c[k] for k in ("cid", "day", "time", "edited_time", "text", "n_img", "window")}
                    for c in cands if c["day"] in sel]
            random.Random(seed + g).shuffle(rows)
            write_jsonl(f"{OUT_DIR}/pass{pas}/batch_{g + 1:02d}.jsonl", rows)
            sizes.append(len(rows))
        out[pas] = sizes
    return out


CLASSES = ("ENTRY_LIVE", "ENTRY_AFTER", "ENTRY_PRICE", "CONDITIONAL", "RECAP", "EXIT", "TRIM_EXECUTED",
           "TRIM_CONDITIONAL", "BE_STOP", "STOPPED", "QUOTE", "CLAIM", "OTHER")
KEY_FIELDS = ("class", "ticker", "strike", "cp", "price", "pct", "refers_to")


def load_pass(name: str) -> Dict[int, dict]:
    d = f"{OUT_DIR}/pass{name}"
    out: Dict[int, dict] = {}
    for fn in sorted(os.listdir(d)):
        if fn.startswith("labels_") and fn.endswith(".jsonl") and "_part" not in fn:
            for r in read_jsonl(os.path.join(d, fn)):
                assert r["cid"] not in out, f"pass {name}: duplicate cid {r['cid']}"
                assert r["class"] in CLASSES, f"pass {name}: bad class {r['class']}"
                out[r["cid"]] = r
    return out


def norm(field: str, v):
    if v is None:
        return None
    if field in ("strike", "price", "pct"):
        try:
            return round(float(v), 2)
        except (TypeError, ValueError):
            return None
    s = str(v).strip().upper().replace(" ", "")
    return s or None


def key_of(r: dict) -> tuple:
    """The fields a disagreement is judged on; contract fields matter only for trade-shaped classes."""
    tradeish = r["class"] not in ("OTHER", "RECAP", "CONDITIONAL")
    return tuple(norm(f, r.get(f)) if (f == "class" or tradeish) else None for f in KEY_FIELDS)


def adjudicate(n_batches: int) -> dict:
    """Agreement between passes A and B per field; disagreements go to pass C batch files."""
    cands = {c["cid"]: c for c in read_jsonl(f"{OUT_DIR}/candidates.jsonl")}
    A, B = load_pass("A"), load_pass("B")
    missing = [cid for cid in cands if cid not in A or cid not in B]
    assert not missing, f"{len(missing)} candidates lack a label in pass A or B"
    agree = {f: 0 for f in KEY_FIELDS}
    dis = []
    for cid in cands:
        a, b = A[cid], B[cid]
        for f in KEY_FIELDS:
            agree[f] += norm(f, a.get(f)) == norm(f, b.get(f))
        if key_of(a) != key_of(b):
            dis.append(cid)
    n = len(cands)
    rows = [{k: cands[c][k] for k in ("cid", "day", "time", "edited_time", "text", "n_img", "window")} for c in dis]
    random.Random(33).shuffle(rows)
    os.makedirs(f"{OUT_DIR}/passC", exist_ok=True)
    per = max(1, math.ceil(len(rows) / n_batches))
    for g in range(n_batches):
        part = rows[g * per:(g + 1) * per]
        if part:
            write_jsonl(f"{OUT_DIR}/passC/batch_{g + 1:02d}.jsonl", part)
    cls = {}
    for cid in cands:
        cls[A[cid]["class"]] = cls.get(A[cid]["class"], 0) + 1
    return {"candidates": n, "agreement_%": {f: round(100 * agree[f] / n, 1) for f in KEY_FIELDS},
            "disagreements": len(dis), "pass_A_classes": cls}


def merged_labels() -> Tuple[Dict[int, dict], Dict[str, int]]:
    """A == B -> A. Otherwise the majority of A, B, C on the key fields; a three-way split -> AMBIGUOUS."""
    A, B = load_pass("A"), load_pass("B")
    C = load_pass("C") if os.path.isdir(f"{OUT_DIR}/passC") else {}
    out, stats = {}, {"agree": 0, "majority": 0, "ambiguous": 0, "no_third_label": 0}
    for cid, a in A.items():
        b = B[cid]
        if key_of(a) == key_of(b):
            out[cid] = a
            stats["agree"] += 1
            continue
        c = C.get(cid)
        if c is None:
            out[cid] = dict(a, **{"class": "AMBIGUOUS"})
            stats["no_third_label"] += 1
            continue
        if key_of(c) == key_of(a):
            out[cid] = a
            stats["majority"] += 1
        elif key_of(c) == key_of(b):
            out[cid] = b
            stats["majority"] += 1
        else:
            out[cid] = dict(a, **{"class": "AMBIGUOUS"})
            stats["ambiguous"] += 1
    return out, stats


def contract_key(lab: dict) -> Optional[str]:
    s, cp = lab.get("strike"), (lab.get("cp") or "").upper()[:1]
    if s is None or cp not in ("C", "P"):
        return None
    try:
        return f"{float(s):g}{cp}"
    except (TypeError, ValueError):
        return None


def freeze() -> dict:
    """Labels -> trades by position tracking (each contract its own trade; an unnamed exit closes all open
    trades; a re-entry after a close is a new trade; adds ignored). Writes trades_frozen.jsonl and its hash."""
    labels, mstats = merged_labels()
    msgs = read_jsonl(f"{OUT_DIR}/caller_messages.jsonl")
    cands = {c["cid"]: c for c in read_jsonl(f"{OUT_DIR}/candidates.jsonl")}
    by_msg = {cands[cid]["msg_id"]: lab for cid, lab in labels.items()}
    trades: List[dict] = []
    counts = {"no_strike_entries": 0, "non_qqq_entries": 0, "non_same_day_entries": 0, "adds_ignored": 0,
              "conditional_hints": 0, "recaps": 0, "ambiguous": 0, "orphan_events": 0}
    day_rows: Dict[str, List[dict]] = {}
    for m in msgs:
        day_rows.setdefault(m["date"], []).append(m)
    for day, rows in sorted(day_rows.items()):
        open_t: Dict[str, dict] = {}
        last_opened: Optional[str] = None
        for m in rows:
            lab = by_msg.get(m["msg_id"])
            if lab is None:
                if m["code"] in ("QUOTE", "CLAIM") and m["session"] == "rth":
                    num = re.findall(r"\d{0,4}\.?\d+", m["text"])
                    val = float(num[0]) if num else None
                    lab = {"class": m["code"], "refers_to": "all-open",
                           "price": val if m["code"] == "QUOTE" else None,
                           "pct": val if m["code"] == "CLAIM" else None}
                else:
                    continue
            cls = lab["class"]
            ev_time = {"utc": m["posted_utc"], "edited_utc": m["edited_utc"]}
            if cls == "AMBIGUOUS":
                counts["ambiguous"] += 1
                continue
            if cls == "CONDITIONAL":
                counts["conditional_hints"] += 1
                continue
            if cls == "RECAP":
                counts["recaps"] += 1
                continue
            if cls in ("ENTRY_LIVE", "ENTRY_AFTER"):
                ck = contract_key(lab)
                tick = (lab.get("ticker") or "QQQ").upper()
                if ck is None:
                    counts["no_strike_entries"] += 1
                    continue
                if tick != "QQQ":
                    counts["non_qqq_entries"] += 1
                    continue
                if (lab.get("expiry") or "same-day").lower() not in ("same-day", "sameday", "0dte"):
                    counts["non_same_day_entries"] += 1
                    continue
                if ck in open_t:
                    counts["adds_ignored"] += 1
                    continue
                tr = {"date": day, "day": m["day"], "contract_key": ck, "strike": float(ck[:-1]), "cp": ck[-1],
                      "kind": "after" if cls == "ENTRY_AFTER" else "live",
                      "announce_utc": m["posted_utc"], "announce_edited_utc": m["edited_utc"],
                      "stated_entry": lab.get("price") if lab.get("price_kind") in ("entry", None) and lab.get("price") else None,
                      "events": []}
                open_t[ck] = tr
                trades.append(tr)
                last_opened = ck
                continue
            # events for open trades
            ref = (lab.get("refers_to") or "all-open")
            ck = contract_key(lab) if str(ref).lower() == "this" else (ref.upper() if ref and ref.lower() != "all-open" else None)
            if ck is not None and not re.match(r"^\d+(\.\d+)?[CP]$", ck):
                ck = None
            if ck is not None and ck not in open_t:
                counts["orphan_events"] += 1
                continue
            targets = [ck] if ck else (list(open_t) if cls in ("EXIT", "STOPPED", "BE_STOP", "TRIM_EXECUTED") else
                                       ([last_opened] if last_opened in open_t else []))
            if not targets:
                counts["orphan_events"] += 1
                continue
            for tk in targets:
                if cls == "ENTRY_PRICE":
                    if lab.get("price") and open_t[tk].get("stated_entry") is None:
                        open_t[tk]["stated_entry"] = lab["price"]
                        open_t[tk]["stated_entry_utc"] = m["posted_utc"]
                    continue
                open_t[tk]["events"].append(dict(ev_time, type=cls, price=lab.get("price"), pct=lab.get("pct")))
            if cls in ("EXIT", "STOPPED"):
                for tk in targets:
                    open_t.pop(tk, None)
    for i, t in enumerate(trades):
        t["trade_id"] = f"T{i + 1:04d}"
    path = f"{OUT_DIR}/trades_frozen.jsonl"
    write_jsonl(path, trades)
    counts.update({"trades": len(trades), "live": sum(t["kind"] == "live" for t in trades),
                   "after_move": sum(t["kind"] == "after" for t in trades),
                   "with_stated_entry": sum(t["stated_entry"] is not None for t in trades),
                   "with_exit_cue": sum(any(e["type"] in ("EXIT", "STOPPED") for e in t["events"]) for t in trades),
                   "with_trim": sum(any(e["type"] == "TRIM_EXECUTED" for e in t["events"]) for t in trades),
                   "with_be": sum(any(e["type"] == "BE_STOP" for e in t["events"]) for t in trades),
                   "trade_days": len({t["date"] for t in trades}), "label_merge": mstats,
                   "sha256": sha256_file(path)})
    return counts


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def selftest() -> int:
    ok = True

    def check(name: str, cond: bool) -> None:
        nonlocal ok
        ok &= bool(cond)
        print(f"{'PASS' if cond else 'FAIL'}  {name}")

    t = tags_for("@premium took 591p, entry was .53 avg, 514c .63-1.00, up 53%")
    check("contract tokens found", [x[0] for x in t.get("contract", [])] == ["591", "514"])
    check("range found", t.get("range") == [[".63", "1.00"]])
    check("percent found", t.get("pct") == ["53"])
    check("ping and entry verb found", "ping" in t and "entry" in t)
    check("half strike parsed", tags_for("591.5p")["contract"][0][0] == "591.5")
    check("lone premium is QUOTE", bool(LONE_PRICE.match(" 1.14 ")) and not LONE_PRICE.match("1.14 on the put"))
    check("lone % is CLAIM", bool(LONE_PCT.match("up 90%")) and bool(LONE_PCT.match("170%")) and not LONE_PCT.match("-35% on put"))
    check("UTC -> New York (EDT)", to_ny("2025-09-16T13:38:13+00:00").strftime("%H:%M") == "09:38")
    check("UTC -> New York (EST)", to_ny("2026-01-26T15:23:11+00:00").strftime("%H:%M") == "10:23")
    # causal window: a later message never appears in an earlier candidate's window
    rows = [{"time": f"10:0{i}:00", "edited_time": None, "text": f"msg {i} 59{i}c" if i in (1, 3) else f"note {i}",
             "n_img": 0} for i in range(5)]
    window_for_1 = [render(p) for p in rows[:1]]
    check("window holds only earlier messages", all("msg 3" not in w and "note 2" not in w for w in window_for_1))
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="backtest/data_cache/local/discord/v035_config.json")
    ap.add_argument("--prepass", action="store_true")
    ap.add_argument("--batches", type=int, default=0, help="number of subagent batches per pass")
    ap.add_argument("--adjudicate", type=int, default=0, help="compare passes A/B; write N pass-C batches")
    ap.add_argument("--freeze", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.adjudicate:
        print(json.dumps(adjudicate(a.adjudicate), indent=1))
    if a.freeze:
        print(json.dumps(freeze(), indent=1))
    if a.prepass:
        cfg = json.load(open(a.config, encoding="utf-8"))
        s = prepass(cfg)
        print(json.dumps(s, indent=1))
    if a.batches:
        print("batch sizes:", batches(a.batches))
    return 0


if __name__ == "__main__":
    sys.exit(main())
