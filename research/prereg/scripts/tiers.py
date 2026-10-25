"""Probe-level tiers for the 201 real probes. Prints a markdown table and the counts."""
import glob
import json
from collections import Counter, defaultdict

ROOT = str(__import__("pathlib").Path(__file__).resolve().parents[2] / "catalogue" / "probes") + "/"
rows = []
for f in sorted(glob.glob(ROOT + "[a-z]*.json")):
    if f.endswith("library.json"):
        continue
    rows += json.load(open(f))
real = {r["probe_id"]: r for r in rows if r["archetype"] != "NONE"}
assert len(real) == 201

# tier, status, note. status: G:<family> gridded | C:<family> collapsed onto | U unspecified | D deferred | I infeasible | - not in T1
T = {
 # CARRY
 "S-CARRY-14b": ("P", "-", "SPX options"), "S-CARRY-14a": ("P", "-", "SPX options"),
 "S-CARRY-15b": ("P", "-", "index options"), "S-CARRY-10a": ("P", "-", "FX forwards"),
 "S-CARRY-02a": ("T2", "-", "spot + premium 1h; Aave leg set to 0 as a labelled adaptation"),
 "S-CARRY-03a": ("T2", "-", "dated-futures + spot 1d; ETH only in half A"),
 "S-CARRY-12b": ("P", "-", "equity index futures"), "S-CARRY-09a": ("P", "-", "FX forwards"),
 "S-CARRY-01a": ("T2", "-", "spot (or index-price) klines for the hedge leg"),
 "S-CARRY-04a": ("P", "-", "no Bybit funding archive (H001 report s.7)"),
 "S-CARRY-04b": ("T2", "-", "coin-margined funding + klines"),
 "S-CARRY-16a": ("P", "-", "Deribit IV history"), "S-BRK-15a": ("P", "-", "option prices"),
 "S-CARRY-15a": ("P", "-", "option strips"), "S-CARRY-16b": ("P", "-", "Deribit IV history"),
 # CLOCK
 "S-CAL-01a": ("T1", "G:C-A", "UTC month boundary"),
 "S-BRK-07a": ("T2", "-", "1h; published UTC windows applied to perps"),
 "S-CAL-08a": ("T2", "-", "1h"), "S-PAT-15a": ("T2", "-", "1h, New York DST mapping"),
 "S-CAL-05a": ("T1", "I", "4 explore seasons"),
 "S-CAL-06b": ("T3", "-", "session boundary at :30 UTC"),
 "S-CAL-07a": ("P", "-", "FX only; no crypto session times published"),
 "S-CAL-04a": ("T1", "I", "4 explore Januaries; size proxied by turnover"),
 "S-CAL-04b": ("P", "-", "equity index, no crypto analog on card"),
 "S-CAL-02a": ("T1", "G:C-B", "weekend vs weekday UTC"),
 # EVENT
 "S-CAL-14a": ("P", "-", "equity and bond futures"),
 "S-CAL-14c": ("T2", "-", "SPX + 10y daily (Yahoo); target ETH/MKT_A10 not BTC"),
 "S-CAL-10b": ("T2", "-", "FOMC calendar"), "S-CAL-13a": ("P", "-", "S&P 500 change list"),
 "S-CAL-11a": ("T2", "-", "macro release calendar"), "S-CAL-15a": ("T2", "-", "expiry calendar (Deribit, recalled)"),
 "S-CAL-10a": ("T2", "-", "1h + FOMC calendar (14:00-14:00 ET variant)"),
 "S-CAL-03a": ("T2", "-", "NYSE holiday calendar"),
 # FLOW_STATE
 "S-CARRY-03b": ("P", "-", "liquidations"), "S-FLOW-10a": ("T2", "-", "dated-futures basis; ETH only in half A"),
 "S-FLOW-11a": ("T2", "-", "CFTC COT (public; reachability unverified); ETH only in half A"),
 "S-FLOW-11b": ("T2", "-", "CFTC COT (public; reachability unverified); ETH only in half A"),
 "S-FLOW-14b": ("P", "-", "labelled exchange flows"), "S-FLOW-14c": ("P", "-", "labelled exchange flows"),
 "S-CARRY-06a": ("T2", "-", "8h hold needs 8h klines"),
 "S-FLOW-10b": ("T1", "G:F-A", "runs only if funnel shows >= 12 windows"),
 "S-FLOW-09a": ("T2", "-", "long/short ratio (metrics)"), "S-FLOW-08a": ("T2", "-", "open interest"),
 "S-FLOW-08b": ("T2", "-", "open interest"), "S-FLOW-07a": ("T2", "-", "open interest; sector map"),
 "S-FLOW-08c": ("T2", "-", "open interest, 1h"), "S-FLOW-02b": ("P", "-", "L1 quotes"),
 "S-FLOW-02a": ("P", "-", "L1 queues"), "S-FLOW-14a": ("P", "-", "on-chain issuance"),
 "S-FLOW-01a": ("T2", "-", "taker-buy columns (held 1d files dropped them)"),
 "S-FLOW-01b": ("P", "-", "signed trade counts"),
 # LEVEL_TOUCH
 "S-PAT-01a": ("T1", "G:L-A", ""), "S-PAT-01b": ("T1", "G:L-B", ""), "S-PAT-02a": ("T1", "G:L-C", ""),
 "S-PAT-02b": ("T1", "G:L-D", ""), "S-PAT-06a": ("T1", "U", "swing window"),
 "S-PAT-06b": ("T1", "U", "swing rule"), "S-PAT-14a": ("T3", "-", "1m"), "S-PAT-07a": ("T2", "-", "1h"),
 "S-PAT-05b": ("T3", "-", "1m"), "S-PAT-05a": ("T3", "-", "1m"), "S-PAT-03b": ("T3", "-", "1m"),
 "S-PAT-04b": ("T3", "-", "1m"), "S-FLOW-06a": ("T3", "-", "1m"), "S-FLOW-06b": ("T3", "-", "1m"),
 "S-PAT-04a": ("T3", "-", "1m"), "S-BRK-02c": ("T1", "G:L-E", ""),
 "S-BRK-10b": ("T1", "C:TS-F", "j unpublished; = Donchian"), "S-PAT-14b": ("T3", "-", "1m"),
 "S-PAT-12a": ("T3", "-", "1m; 24/7 session invented"),
 # MODEL
 "S-MOD-09a": ("P", "-", "on-chain, tweet, cross-asset minute features"),
 "S-MOD-10a": ("P", "-", "accounting characteristics"),
 "S-MOD-06a": ("T1", "D", "composite model"), "S-MOD-11a": ("T1", "D", "composite model"),
 "S-MOD-14a": ("T1", "D", "evolved rules; every rule is a trial"),
 "S-MOD-01b": ("T1", "D", "3000-day fit window exceeds history"),
 "S-MOD-01a": ("T1", "D", "3000-day fit window exceeds history"),
 "S-XS-02b": ("T1", "G:XS-H", "lag 1 collapses onto XS-G"), "S-MR-13a": ("T1", "G:XS-P", ""),
 "S-MR-13b": ("P", "-", "sector ETFs"), "S-MR-13c": ("P", "-", "sector-ETF factor"),
 # TS_STATE
 "S-BRK-07b": ("T2", "-", "1h, UTC windows"), "S-BRK-08c": ("T1", "G:TS-M", ""), "S-MR-03a": ("T1", "C:TS-M", "= S-BRK-08c, opposite sign"),
 "S-MR-05a": ("T1", "G:TS-M", ""), "S-MR-05b": ("T1", "G:TS-M", ""),
 "S-BRK-10a": ("T1", "C:TS-F", "grid published as ranges only"),
 "S-TREND-10a": ("T1", "G:TS-L", "ATR(10) x 3 recalled, flagged"), "S-TREND-11a": ("T1", "G:TS-L", ""),
 "S-MR-07b": ("T1", "U", "N not published"), "S-TREND-08a": ("T1", "G:TS-K", ""),
 "S-BRK-09a": ("T1", "G:TS-F", ""), "S-BRK-11a": ("T1", "C:TS-F", "lookbacks unpublished"),
 "S-MR-07a": ("T1", "G:TS-F", "SMA200 gate stripped"), "S-TREND-07a": ("T1", "C:TS-F", "= 20"),
 "S-TREND-07b": ("T1", "C:TS-F", "= 55"), "S-TREND-07c": ("T1", "C:TS-F", "lookback unpublished"),
 "S-TREND-16a": ("T1", "G:TS-F", ""), "S-TREND-06a": ("T1", "G:TS-K", ""),
 "S-CAL-14b": ("P", "-", "equity and bond futures"), "S-FLOW-13a": ("P", "-", "vendor index; thresholds unpublished"),
 "S-BRK-13a": ("P", "-", "no session gap in perps"), "S-BRK-13b": ("P", "-", "no session gap in perps"),
 "S-MR-14a": ("P", "-", "no session gap in perps"), "S-TREND-14a": ("T1", "G:TS-K", ""),
 "S-TREND-13a": ("T1", "G:TS-K", ""), "S-MR-06a": ("T1", "G:TS-N", "no close auction in perps"),
 "S-TREND-06b": ("T1", "G:TS-K", ""), "S-XS-10b": ("T1", "U", "expectation model and horizon"),
 "S-BRK-05a": ("P", "-", "needs a cash open"), "S-BRK-06a": ("T3", "-", "5m"),
 "S-BRK-06b": ("T2", "-", "1h for an honest intraday entry"), "S-BRK-01b": ("T1", "G:TS-N", "state at close, 10-day hold"),
 "S-BRK-03a": ("P", "-", "needs a cash open"), "S-BRK-04a": ("P", "-", "US stock intraday"),
 "S-MR-11a": ("T1", "G:TS-O", ""), "S-MR-12a": ("T1", "G:TS-O", ""),
 "S-MR-16a": ("T1", "C:TS-O", "1d variant of a 5m/1h/1d study; formation and trading periods unpublished"), "S-MR-16b": ("T1", "C:TS-O", "1d variant of a 5m/1h/1d study; formation and trading periods unpublished"),
 "S-MOD-07a": ("T1", "G:TS-D", "on MKT_A10"), "S-MOD-09b": ("T3", "-", "1m"),
 "S-MOD-11b": ("T1", "G:TS-B", ""), "S-MR-10a": ("T1", "G:TS-E", "on MKT_A10"), "S-MR-15b": ("T3", "-", "15m"),
 "S-TREND-01a": ("T1", "G:TS-A", "36-month hold infeasible"), "S-TREND-02a": ("T1", "G:TS-A", ""),
 "S-TREND-02b": ("T1", "G:TS-A", ""), "S-TREND-02c": ("T1", "C:TS-A", "duplicate of S-TREND-01a"),
 "S-TREND-15a": ("T1", "G:TS-C", ""), "S-PAT-13a": ("T3", "-", "1m; box size unpublished"),
 "S-TREND-03a": ("T1", "G:TS-J", ""), "S-MR-04a": ("T1", "G:TS-N", ""), "S-PAT-13b": ("T3", "-", "1m; brick size unpublished"),
 "S-MR-01a": ("T1", "G:TS-M", "SMA200 gate stripped"), "S-MR-02a": ("T1", "G:TS-M", ""),
 "S-FLOW-12a": ("P", "-", "Google Trends"), "S-TREND-04a": ("T1", "G:TS-G", ""), "S-TREND-04b": ("T1", "G:TS-H", ""),
 "S-TREND-05a": ("T1", "G:TS-I", ""), "S-MOD-02a": ("T1", "G:TS-O", "pairs from S-MR-11a"),
 "S-MR-02b": ("T1", "C:TS-M", "14 = S-MR-02c; 5 and 9 lack an extreme level"), "S-MR-02c": ("T1", "G:TS-M", ""),
 "S-TREND-12a": ("T1", "G:TS-K", ""), "S-BRK-04b": ("P", "-", "US stock intraday"),
 "S-FLOW-05a": ("T1", "G:XS-S", "own-volume spike, long-short"), "S-FLOW-05b": ("T1", "G:XS-T", ""),
 "S-MR-08a": ("T3", "-", "1m"),
 # VOL_STATE
 "S-TREND-08b": ("T1", "G:V-A", ""), "S-BRK-08a": ("T1", "G:V-B", ""), "S-MOD-06b": ("T1", "D", "GP changepoint feature"),
 "S-MOD-01c": ("T1", "D", "jump-model feature, no threshold"), "S-BRK-14b": ("T1", "G:V-H", ""),
 "S-TREND-01b": ("T1", "G:V-H", ""), "S-BRK-02b": ("T1", "G:V-D", ""), "S-BRK-01a": ("T1", "G:V-F", "NR range -> NR4/NR7"),
 "S-BRK-02a": ("T1", "G:V-E", ""), "S-MOD-04a": ("T1", "G:V-H", ""), "S-BRK-14a": ("T1", "C:V-H", "= S-MOD-04a"),
 "S-TREND-04c": ("T1", "G:V-G", ""), "S-BRK-08b": ("T1", "G:V-C", ""), "S-FLOW-04a": ("T3", "-", "1m"),
 # XS_RANK
 "S-XS-16a": ("P", "-", "on-chain addresses"), "S-XS-10a": ("T1", "I", "1-year formation and hold: 4 windows"),
 "S-CARRY-11a": ("P", "-", "commodity curves"), "S-CARRY-12a": ("P", "-", "equity index futures"),
 "S-XS-06a": ("T1", "G:XS-N", ""), "S-CARRY-13a": ("P", "-", "bond yields"), "S-XS-05a": ("T1", "G:XS-J", ""),
 "S-XS-14a": ("T1", "G:XS-K", "volume-only split: all perps Large&Liquid"), "S-XS-12c": ("T1", "U", "volume window"),
 "S-CAL-12b": ("P", "-", "earnings"), "S-CAL-12a": ("P", "-", "earnings"), "S-CARRY-08a": ("P", "-", "FX forwards"),
 "S-CARRY-05b": ("T3", "-", "5m"), "S-CARRY-05a": ("T1", "G:XS-R", "funding file needed for every U50A coin"),
 "S-MR-06b": ("T1", "G:XS-Q", "no close auction in perps"), "S-XS-07a": ("T1", "G:XS-M", "residuals vs MKT_A10"),
 "S-BRK-16a": ("P", "-", "implied vol"), "S-XS-04a": ("P", "-", "coin sector map"), "S-XS-11a": ("P", "-", "market cap"),
 "S-XS-11b": ("P", "-", "book-to-market"), "S-XS-12b": ("P", "-", "market cap"), "S-XS-08a": ("T1", "G:XS-L", ""),
 "S-MOD-08a": ("T1", "D", "ML ensemble over 31 lookbacks"), "S-MOD-10b": ("T1", "C:XS-B", "lookbacks unpublished"),
 "S-MR-09a": ("T1", "G:XS-F", ""), "S-MR-09b": ("P", "-", "industry portfolios"), "S-MR-15a": ("T1", "G:XS-G", "1d and 1w collapse onto XS-F, XS-B"),
 "S-MR-15c": ("T2", "-", "12h returns"), "S-XS-01a": ("T1", "G:XS-A", ""), "S-XS-02a": ("T1", "G:XS-C", "no-skip collapses onto XS-B"),
 "S-XS-12a": ("T1", "G:XS-B", ""), "S-XS-13a": ("T1", "G:XS-B", "volume-only split"), "S-XS-13b": ("T1", "G:XS-E", ""),
 "S-XS-13c": ("T1", "G:XS-D", ""), "S-XS-15a": ("T1", "G:XS-I", "size split dropped"),
 "S-CAL-06a": ("T3", "-", "session boundary at :30 UTC"), "S-XS-16b": ("P", "-", "on-chain addresses"),
 "S-XS-09a": ("T3", "-", "intraday interval unspecified (1m on card)"), "S-XS-03a": ("T1", "G:XS-O", "residuals vs MKT_A10"),
 "S-CARRY-07a": ("P", "-", "staking yields"),
}
missing = set(real) - set(T)
extra = set(T) - set(real)
assert not missing and not extra, (missing, extra)

tiers = Counter(v[0] for v in T.values())
print("tiers:", dict(tiers), "total", sum(tiers.values()))
by = defaultdict(Counter)
for pid, (t, s, n) in T.items():
    by[real[pid]["archetype"]][t] += 1
print("| archetype | T1 | T2 | T3 | P | total |")
print("|---|---|---|---|---|---|")
for a in sorted(by):
    c = by[a]
    print(f"| {a} | {c['T1']} | {c['T2']} | {c['T3']} | {c['P']} | {sum(c.values())} |")
st = Counter()
for pid, (t, s, n) in T.items():
    if t == "T1":
        st[s.split(":")[0]] += 1
print("T1 status:", dict(st))

print("\n| probe | archetype | variable | bar | tier | phase-2 status | note |")
print("|---|---|---|---|---|---|---|")
lab = {"G": "grid", "C": "collapsed onto", "U": "unspecified", "D": "deferred (composite)", "I": "infeasible", "-": "-"}
for pid in sorted(T, key=lambda p: (real[p]["archetype"], T[p][0], real[p]["variable"], p)):
    t, s, n = T[pid]
    k = s.split(":")
    stat = lab[k[0]] + (" " + k[1] if len(k) > 1 else "")
    r = real[pid]
    print(f"| {pid} | {r['archetype']} | {r['variable']} | {r['bar']} | {t} | {stat} | {n} |")
