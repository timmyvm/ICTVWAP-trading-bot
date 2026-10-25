"""
v0.37-exp part G — the caller's own pre-open levels, extracted blind and double-coded (DEVLOG v0.37-exp).

Input: backtest/data_cache/local/discord/v036/bias_days.jsonl (discord_bias_calls.py --prepass: pre-open
analysis posts per session, dates blinded). Two independent subagent passes write levelsA.jsonl and
levelsB.jsonl; --freeze keeps only the rules both passes extracted identically and prints their hash.

Rubric (the coders get this text verbatim). For each session, list every CONDITIONAL LEVEL RULE stated in
the text, i.e. a price level plus the move he expects once price is beyond it:
  {"level": 515.0, "side": "above"|"below", "direction": "UP"|"DOWN", "targets": [518.0, 520.0],
   "instrument": "QQQ"|"SPY"|"SPX"|"NQ"|"OTHER"|"UNKNOWN"}
  - "hold above 515 we can see 518, 520" -> level 515, above, UP, targets [518, 520]
  - "lose 512 and we drop to 508" -> level 512, below, DOWN, targets [508]
  - "566 is our pivot: above calls, below puts" -> two rules (566 above UP, 566 below DOWN), targets []
  - "reject 520 for puts to 515" -> level 520, below, DOWN, targets [515] (rejected = stays below)
  Only numbers written in the text count (never guess levels from images). Targets are listed nearest first.
  A bare level with no expected direction is not a rule. instrument is the ticker the numbers refer to;
  UNKNOWN when the text does not say and the post is not clearly about one ticker. Use the LAST statement
  when he revises the same level before the open.

Agreement: a rule is frozen when both passes give the same (level within 0.01, side, direction,
instrument); its targets are frozen only where both passes list the same first target (else none).

  python3 backtest/discord_levels.py --freeze
  python3 backtest/discord_levels.py --selftest
"""

import argparse
import hashlib
import json
import sys
from collections import Counter
from typing import Dict, List, Tuple

OUT = "backtest/data_cache/local/discord/v036"
SIDES, DIRS = ("above", "below"), ("UP", "DOWN")
INSTR = ("QQQ", "SPY", "SPX", "NQ", "OTHER", "UNKNOWN")


def load(path: str) -> Dict[int, List[dict]]:
    out: Dict[int, List[dict]] = {}
    for line in open(path, encoding="utf-8"):
        if not line.strip():
            continue
        r = json.loads(line)
        rules = []
        for x in r.get("rules", []):
            assert x["side"] in SIDES and x["direction"] in DIRS and x["instrument"] in INSTR, f"bad rule {x}"
            rules.append({"level": float(x["level"]), "side": x["side"], "direction": x["direction"],
                          "targets": [float(t) for t in x.get("targets", [])], "instrument": x["instrument"]})
        out[int(r["day"])] = rules
    return out


def key(r: dict) -> Tuple[float, str, str, str]:
    return (round(r["level"], 2), r["side"], r["direction"], r["instrument"])


def agree(a: Dict[int, List[dict]], b: Dict[int, List[dict]]) -> Tuple[Dict[int, List[dict]], Counter]:
    frozen: Dict[int, List[dict]] = {}
    c = Counter()
    for day in sorted(set(a) | set(b)):
        ra, rb = a.get(day, []), b.get(day, [])
        kb = {key(r): r for r in rb}
        keep = []
        for r in ra:
            m = kb.pop(key(r), None)
            if m is None:
                c["only in pass A"] += 1
                continue
            same_t1 = bool(r["targets"]) and bool(m["targets"]) and abs(r["targets"][0] - m["targets"][0]) < 0.011
            keep.append(dict(r, targets=[r["targets"][0]] if same_t1 else []))
            c["agreed"] += 1
            c["agreed with a common first target"] += same_t1
        c["only in pass B"] += len(kb)
        if keep:
            frozen[day] = keep
    return frozen, c


def freeze() -> int:
    a, b = load(f"{OUT}/levelsA.jsonl"), load(f"{OUT}/levelsB.jsonl")
    print(f"sessions: pass A {len(a)}, pass B {len(b)}; rules: A {sum(map(len, a.values()))}, B {sum(map(len, b.values()))}")
    frozen, c = agree(a, b)
    print(dict(c))
    rules = [r for v in frozen.values() for r in v]
    print(f"frozen sessions {len(frozen)}, rules {len(rules)}; by instrument {dict(Counter(r['instrument'] for r in rules))}; "
          f"by direction {dict(Counter(r['direction'] for r in rules))}")
    path = f"{OUT}/levels_frozen.jsonl"
    with open(path, "w", encoding="utf-8") as f:
        for day in sorted(frozen):
            f.write(json.dumps({"day": day, "rules": frozen[day]}) + "\n")
    print("sha256", hashlib.sha256(open(path, "rb").read()).hexdigest())
    return 0


def selftest() -> int:
    ok = True

    def check(name: str, cond: bool) -> None:
        nonlocal ok
        ok &= bool(cond)
        print(f"{'PASS' if cond else 'FAIL'}  {name}")

    r = lambda lvl, side, d, t, i="QQQ": {"level": lvl, "side": side, "direction": d, "targets": t, "instrument": i}
    a = {1: [r(515, "above", "UP", [518, 520]), r(512, "below", "DOWN", [508])], 2: [r(600, "above", "UP", [])]}
    b = {1: [r(515.0, "above", "UP", [518]), r(512, "below", "DOWN", [507])], 2: [r(600, "above", "UP", [], "SPY")]}
    fr, c = agree(a, b)
    check("same level/side/direction/instrument -> frozen", len(fr.get(1, [])) == 2)
    check("first targets agree -> kept, else dropped", fr[1][0]["targets"] == [518] and fr[1][1]["targets"] == [])
    check("instrument disagreement -> excluded", 2 not in fr and c["only in pass A"] == 1 and c["only in pass B"] == 1)
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--freeze", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.freeze:
        return freeze()
    return 0


if __name__ == "__main__":
    sys.exit(main())
