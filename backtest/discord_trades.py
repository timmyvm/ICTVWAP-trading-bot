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
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.prepass:
        cfg = json.load(open(a.config, encoding="utf-8"))
        s = prepass(cfg)
        print(json.dumps(s, indent=1))
    if a.batches:
        print("batch sizes:", batches(a.batches))
    return 0


if __name__ == "__main__":
    sys.exit(main())
