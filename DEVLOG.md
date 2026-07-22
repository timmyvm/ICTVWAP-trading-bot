# DEVLOG — Powell Trades Bot

Living record of every version: what changed, which bugs were found/fixed,
what the backtest said, and what's open. **Update this file with every code or
config change** (rule in CLAUDE.md). Newest version at the top.

Conventions:
- Version bumps: any strategy/execution behavior change = minor bump; pure
  docs/tooling = patch note under the current version.
- Every entry links commits and, when behavior changed, the backtest evidence
  (`run_backtest.py`, exact flags) that justified it.
- Baseline benchmark: 180d ICT-only run, `VWAP_ENABLED=false
  ENFORCE_TIER_RR=false python run_backtest.py --days 180 --variant fixed`.

---

## v0.4.1 — TP floor rejects instead of retargeting (2026-07-21)

**Negative result, documented.** v0.4's TP floor *retargeted* to the next
liquidity pool when the nearest one sat inside the fee zone. Validation
(180d ICT-only): **105 trades, 25.7 % win, net −$5,311, −53.1 %, PF 0.39** —
far worse than the v0.3 baseline (22 trades, −5.6 %, PF 0.71). Lesson: the
nearest pool is load-bearing for the ~45 % win rate — price reliably reaches
the first draw, not the second. Retargeting converted a high-win/small-target
system into a low-win/far-target system the entries can't support, and let
through dozens of signals the small targets used to reject via R:R.

**Change** `_build_signal` keeps the TRUE nearest DOL as TP and REJECTS the
signal when that target is closer than `MIN_TP_DISTANCE_PCT` — no substitute
targets. Trade count should now fall below baseline (near-target setups are
skipped), win rate should hold near baseline on survivors.

**Backtest (2026-07-22)** — corrected 180d ICT-only validation vs v0.3
baseline (22 trades / 45.5 % win / gross +$378 / net −5.6 % / PF 0.71):
**7 trades, 28.6 % win, gross −$76, fees $352, net −$428 (−4.3 %), PF 0.47.**
NEGATIVE. The gates removed February's small-target winners (the win rate
lived in nearest-pool quick hits the TP floor now skips) while two March
longs still slipped through the trend gate's ±0.5 % neutral band and lost
−$323. Net was smaller only because there were fewer trades — risk reduction,
not edge. Both gate defaults reverted to OFF (v0.4.2); v0.3 behavior is the
tested least-bad configuration.

## v0.7 — R4: the 2022-model FVG entry (2026-07-22)

**Change** `ENTRY_TRIGGER="fvg"` (default stays "rb"): entries become resting
limits at the CE of a fresh displacement fair value gap (≤ FVG_MAX_AGE_CANDLES
old, not yet traded through, CE inside the fib zone). Everything downstream —
stops, targets, R:R, tiers — unchanged via a RejectionBlock-shaped adapter.
Rationale: every failed filter *delayed* entries; the FVG limit improves entry
PRICE (fills on the retrace or not at all). This is Huddleston's actual 2022
entry, untested until now.

**Experimental config**: v0.3 stack + fvg trigger ONLY (all v0.5/v0.6 gates
off) so the trigger is the single variable vs the v0.3 baseline.

**Pre-registered criteria** (vs baseline 22 tr / 45.5 % / +$378 gross /
PF 0.71): gross/trade ≥ baseline's +$17; win rate ≥ ~40 %; trades ≥ 12;
fill rate of placed orders reported (limit-at-CE may fill less often).
**Hard stop**: this is trial #7 — whatever the outcome, signal-side iteration
ends here; results are in-sample evidence only until walk-forward validation.

**Backtest (2026-07-22): FAIL on pre-registered criteria.** 180d ICT-only:
**7 trades, 28.6 % win, gross −$242, fees $280, net −$523, PF 0.30.**
Orders: 14 placed → **7 filled (50 %)**, 7 replaced unfilled. Criteria
(gross/trade ≥ +$17, win ≥ 40 %, trades ≥ 12): all missed. Trades preserved
at `backtest/baselines/v07_180d_trades.csv`.

Mechanism — textbook **adverse selection on passive fills**, exactly as the
market-maker's-dilemma literature (RESEARCH.md §2) predicted: displacements
strong enough to run never retrace to the CE (those winners go unfilled),
while the gaps that DO retrace deep enough to fill are disproportionately the
failing ones. The entry price improved; the entry *population* got worse.

## v0.7.2 — CORRECTION: v0.7 was confounded; true v0.3+FVG rerun (2026-07-22)

**Design flaw found (user-caught):** the v0.7 run disabled the v0.5/v0.6
FLAGS via env, but the killzone times were plain constants still set to the
ICT windows (8:30-11 / 2-5) — so v0.7 actually tested FVG entries + shifted
sessions, not FVG alone. Sessions are now env-controllable
(`NY_AM_SESSION`/`LONDON_SESSION`) and the true single-variable experiment
(v0.3 stack incl. proven windows + `ENTRY_TRIGGER=fvg`) is running. Same
pre-registered criteria as v0.7. The v0.7 FAIL verdict stands but is
re-labeled "FVG + ICT killzones".

**Process lesson (also added to CLAUDE.md):** before claiming a
single-variable run, diff the FULL effective config against the baseline —
flags are not the only config.

**Backtest (2026-07-22): quality criteria PASS, activity criterion FAIL —
the most promising variant tested.** 180d ICT-only, true single variable:
**8 trades, 50.0 % win, gross +$233 (+$29/trade), fees $311, net −$78
(−0.8 %), PF 0.87.** Fills 8/16 (50 %). Trades preserved at
`backtest/baselines/v072_180d_trades.csv`.

Criteria: gross/trade ≥ +$17 → **+$29 PASS**; win ≥ 40 % → **50 % PASS**;
trades ≥ 12 → **8 FAIL**. By the pre-registered letter the production default
stays "rb" — but unlike v0.4–v0.6, the activity drop came WITH quality
improvement, and the confound resolution is decisive: same trigger under ICT
sessions won 28.6 %, under the proven sessions 50 % — the session shift, not
the trigger, wrecked the first FVG run.

Fee sweep comparison (analytic, from preserved trade lists):

| Config | n | Bybit (0.02/0.055) | VIP (0.01/0.03) | Rebate (0/0.02) | Free |
|---|---|---|---|---|---|
| v0.3 RB | 22 | −$562 | −$114 | +$202 | +$378 |
| v0.3+FVG | 8 | **−$78** | **+$70** | +$178 | +$233 |

The FVG variant is fee-robust: near-breakeven at retail fees and net-positive
from VIP-ish tiers up (better entry prices → more gross per unit of notional).
v0.3 RB out-earns it only in near-zero-fee regimes (volume advantage).

**Status**: `ENTRY_TRIGGER=fvg` is the designated walk-forward candidate.
8-trade sample + ~8th configuration examined = heavy statistical discount;
neither config displaces the other without out-of-sample survival. Signal
iteration remains CLOSED; next steps are venue selection and walk-forward
of BOTH configs on new data as it accrues.

## v0.7.1 — SETTLEMENT: production config = v0.3 behavior (2026-07-22)

Seven configurations tested; final map:

| Config | Trades | Win % | Gross | Net | PF |
|---|---|---|---|---|---|
| legacy (original) | 0 ICT / 73 VWAP | — | — | −45.1 % | 0.12 |
| **v0.3 (bug fixes, tier off)** | **22** | **45.5** | **+$378** | **−5.6 %** | **0.71** |
| v0.4.1 (TP retarget→reject) | 105→7 | 25.7→— | −$1,531 | −53 % | 0.39 |
| v0.5 (D1 + plain MSS) | 14 | 21.4 | −$522 | −11.8 % | 0.30 |
| v0.6 (+ sweep-coupled MSS, R2, R3) | 12 | 25.0 | −$436 | −10.3 % | 0.26 |
| v0.7 (FVG-CE entries) | 7 | 28.6 | −$242 | −5.2 % | 0.30 |

All flag defaults now encode v0.3 behavior (anchors/gates off, RB trigger,
proven killzones); every alternative remains one env var away. **v0.3 is the
only gross-positive configuration**, and with the fee sweep it is net-positive
(+$202/180d) at 0.00/0.02 venue rates. Signal-side iteration is CLOSED per the
pre-registered hard stop; any future signal claim requires walk-forward /
out-of-sample survival before it can displace v0.3. Next levers are
structural: venue/fee selection, then live-order lifecycle hardening.

## v0.6 — ICT alignment pack: R1+R2+R3 from the 2022 Mentorship (2026-07-22)

**Changes** (individually flagged so any piece can be ablated without edits)
- R1 `REQUIRE_MSS_SWEEP` (on): the 15m structure break only arms entries when
  the move before it wicked through opposite-side liquidity within 4h —
  Ep3's "sweep first, then shift; a break without a sweep is noise".
- R2 `DAILY_LEVELS_IN_DOL` (on): old daily swing highs/lows join the DOL/TP
  map (Ep2: the daily chart is the liquidity map).
- R3 killzones: NY 9:30-12:00 → **8:30-11:00**, London 3-6 → **2-5** (Ep3).

**Pre-registered success criteria** (vs v0.3 baseline 22 tr / 45.5% / +$378
gross, and vs v0.5 result): gross/trade up; win rate not materially below
baseline; trade count 10-30 (R3 widens mornings, R1 filters — net ambiguous);
March counter-trend cluster reduced. Bundle judged as a whole; if negative,
ablate flags individually before reverting.

**Backtest (2026-07-22): FAIL on pre-registered criteria.** 180d ICT-only:
**12 trades, 25.0 % win, gross −$436, fees $594, net −$1,030, PF 0.26**
(baseline: 22 / 45.5 % / +$378 / −$562 / 0.71). Trades preserved at
`backtest/baselines/v06_180d_trades.csv`. The sweep-coupled MSS was more
selective (12 vs 14 trades) and marginally less bad than v0.5 per trade, but
the family pathology is unchanged: close-confirmed 15m gating admits LATE
entries, and the D1 anchor's swing-blindness persists. Criteria (gross/trade
up, win rate ≈ baseline, March cluster reduced): all missed. Conclusion: the
v0.5/v0.6 confirmation-layer family is rejected; v0.3 remains the best RB
configuration. Flag defaults to be settled after the v0.7 (FVG-entry) trial.

## v0.5 — Top-down multi-timeframe: D1 anchor + M15 MSS (2026-07-22)

**Changes** (one structural change, per the one-variable rule)
- `DAILY_BIAS_ANCHOR` (default on): daily candles added to the data layer;
  bias is now hierarchical — D1 structure governs direction, the existing
  4H/1H read refines it. D1+LTF agreement trades; **D1 vs LTF conflict =
  NEUTRAL** (the March trap: a 4H retrace break against the daily trend);
  D1 neutral = v0.3 behavior.
- `REQUIRE_15M_MSS` (default on): before any RB scan, a 15m close must have
  broken a 15m swing level in the bias direction within the last 8 closed
  15m candles (2h). Execution only arms after structure has actually shifted.
- Entries/stops/targets untouched.

**Pre-registered success criteria (written BEFORE the validation run):**
1. March counter-trend longs mostly blocked (baseline: 6 longs, −$640 net).
2. Jan–Feb aligned winners mostly retained (baseline: +$184 net).
3. Gross edge per trade up meaningfully vs baseline (+$17/trade).
4. Trade count ≥ ~12/180d (a collapse below that = over-filtering, reject).
If these fail, v0.5 reverts like v0.4.1 did and signal-side iteration STOPS.

**Backtest (2026-07-22): FAIL on pre-registered criteria.** 180d ICT-only:
**14 trades, 21.4 % win, gross −$522, fees $655, net −$1,178, PF 0.30**
(baseline: 22 / 45.5 % / +$378 / −$562 / 0.71). Trades preserved at
`backtest/baselines/v05_180d_trades.csv`.

Criteria: (1) March longs blocked — **NO**: March −$648, 0 wins. Mechanism:
in a relentless daily decline no daily swing lows FORM (monotonic series has
no local minima), so the D1 read goes NEUTRAL and the veto goes blind exactly
when it's needed. (2) Feb winners retained — **NO**: 3 trades −$33 vs 12 for
+$184; the plain M15 MSS gate choked off the chop entries. (3) Gross/trade up
— **NO**: −$37 vs +$17. Additional pathology: even shorts lost (11 for −$683
vs +$78 baseline) — waiting for a 15m close-through-swing admits entries LATE
in the leg, at worse prices. Lesson: close-confirmed M15 MSS is a lag filter,
not a quality filter; and a structural D1 anchor needs a fallback read (e.g.
close vs prior day's range) for swing-less trend days.

**Fee sweep (2026-07-22)** — computed analytically from the regenerated and
byte-identical v0.3 baseline (22 trades, preserved at
`backtest/baselines/v03_180d_trades.csv`); trade list is fee-independent:

| Fee scenario (maker/taker %) | 180d net |
|---|---|
| Bybit non-VIP (0.02 / 0.055) | **−$562** |
| VIP-ish (0.01 / 0.03) | −$114 |
| Rebate venue (0.00 / 0.02) | **+$202** |
| Zero fees | +$378 |

The unmodified v0.3 signal is net-POSITIVE on a 0.00/0.02 venue with no
strategy changes — execution cost, not signal quality, is the binding
constraint. (22-trade sample caveat applies.)

**ICT source study** — 2022 Mentorship Ep2/Ep3 transcripts distilled into
`docs/ict/distilled_rules.md`: sweep-coupled MSS (R1), daily extremes in the
DOL map (R2), killzone alignment (R3), FVG entries (R4) queued as future
single-change experiments. Ep2/Ep3 explicitly teach "closest target, low
hanging fruit" — independent confirmation of the nearest-DOL TP design and
of v0.4.1's negative retargeting result.

## v0.4.2 — Gate defaults reverted to off (2026-07-22)

**Change** `TREND_ALIGNMENT_FILTER` default → false, `MIN_TP_DISTANCE_PCT`
default → 0.0. Code paths retained for isolated testing.

**Conclusion after 4 tested configurations** (legacy, v0.3, v0.4-retarget,
v0.4.1): none is net-profitable at Bybit non-VIP fees; v0.3 keeps the only
positive gross edge (+$378/180d, eaten 2.5× by fees). Per the overfitting
literature (RESEARCH.md #3), further parameter iteration on 7–22-trade
samples manufactures noise. Remaining levers are structural: execution costs
(VIP/maker tiers, rebate venue), instrument choice (larger %-moves relative
to costs), or accepting the strategy as discretionary-only.

## v0.4 — Trend gate + fee-aware targets (2026-07-21) `c609d33`

**Changes**
- `TREND_ALIGNMENT_FILTER` (default on): block entries whose bias fights the
  broad 4H trend (last 4H close vs 50-period 4H SMA, ±0.5 % neutral band).
  Evidence: all 6 losing longs in the v0.3 180d run were counter-trend
  entries into the March crash; Osler's cascade asymmetry (RESEARCH.md).
- `MIN_TP_DISTANCE_PCT` (default 0.25 %): TP floor — **initial retargeting
  implementation was wrong, see v0.4.1.**

**Open**
- If trade count collapses under the 0.25 % TP floor, retest at 0.15 %.
- Walk-forward / PBO validation of any positive result (RESEARCH.md #5).

## v0.3 — Rulebook-faithful execution model (2026-07-21) `1137f64`..`695a16b`

**Changes**
- Backtest fills follow the rulebook's "limit orders only": maker entries,
  maker take-profits, taker+slippage stops only. Order lifecycle counters.
- `ATR_LOW_THRESHOLD` 1.2 → 0.8: the 1.2 came from the VWAP rulebook's
  *strategy-selection* ratio, not an entry-timeframe rule; at 1.2 the switcher
  pinned the bot to 1m mode against the ICT rulebook's "5m default for
  crypto".
- `VWAP_ENABLED` kill switch (default on to preserve behavior).
- `fixed_nwog` backtest variant; docs: BACKTEST_REPORT.md results,
  RESEARCH.md sourced synthesis.

**Backtest**
- 60d, 4 variants: legacy −45.1 % (ICT 0 trades ever) · fixed −42.6 % (ICT 0
  via tier floors) · fixed_notier −42.1 % (ICT 5 trades, 60 % win, +$95,
  PF 1.42; VWAP −$4,307 of which $3,652 fees) · fixed_nwog identical (override
  had zero effect in window).
- 180d ICT-only (baseline): 22 trades, 45.5 % win, gross +$378, fees $940,
  net −$562 (−5.6 %), PF 0.71, max DD 12.2 %, median hold 3 min. Decomposition:
  March longs −$825 (0 wins), shorts overall +$78 net, longs −$640.

**Key insight** ICT has a real gross edge that fees are 2.5× too big for;
VWAP's median move (0.083 %) ≈ its round-trip cost — structurally unviable at
non-VIP fees regardless of signal quality.

## v0.2 — The audit: 16 bugs (2026-07-21) `fffdad9`

**Show-stoppers fixed**
1. Fib leg validity contradicted the entry condition (`recent_low >
   equilibrium` vs RB requiring ≥ 0.5 retrace) — **ICT could never fire a
   single trade**. Now structural (origin swing unbroken); `FIB_VALIDITY_MODE`
   legacy kept for comparison.
2. Bybit's forming candle treated as a closed confirmation candle everywhere —
   feed now drops it (`drop_forming=True`).
3. NWOG could never be computed (200×1m fetch can't span Fri→Sun) — targeted
   weekend-anchor fetch.
4. Re-entry budget burned by side-effecting `can_re_enter()` called every tick
   — split peek/`record_re_entry()`; setup identity = fib leg, not RB
   timestamp.
5. Judas swing direction detected but never used — wired as directional gate.
6. Fresh clone crashed at boot (`logs/` gitignored, FileHandler at import).
7. Midnight/10AM opens scrolled out of the 200×1m window by NY AM — depth
   1000 + vectorized lookup.

**Quality/economics fixed**
8. NWOG override stuck BEARISH forever after gap fill; now clears, opt-in
   (`NWOG_BIAS_OVERRIDE`, default off).
9. VWAP breakeven moved stop to the ±1σ band instead of entry; paper CSV
   never updated.
10. Paper tracking resolved only the last CSV row — concurrent trades orphaned.
11. VWAP traded minutes after midnight reset on degenerate 2-candle bands —
    `VWAP_MIN_SESSION_CANDLES` warm-up.
12. Regime flapped on single-candle TR — 3-candle mean.
13. Stop buffers hard-coded at 2.0 *points* (~0.003 % of BTC) — now
    `STOP_BUFFER_PCT` (0.1 %).
14. No notional cap on sizing — `MAX_LEVERAGE` (10×).
15. No fees/slippage anywhere; paper PnL in points without qty —
    `TAKER_FEE_PCT`/`MAKER_FEE_PCT`/`SLIPPAGE_PCT`, backtester charges them.
16. Tier R:R floors (1:5/1:3) starve signals — kept (documented design) but
    toggleable via `ENFORCE_TIER_RR`.

**Tooling** `backtest/` package: paginated Bybit fetcher + committed 180d 1m
BTC cache, event-driven engine reusing the real strategy stack (injected
clock, windowed frames, limit fills, intrabar SL/TP, conservative stop-first),
`run_backtest.py` CLI with variants.

## v0.1 — Original (pre-audit) `8123179`, `26102fb`

ICT (bias → fib → rejection block → DOL targets) + VWAP ±2σ mean reversion on
Bybit testnet, paper mode. Non-functional: ICT structurally unable to trade,
paper stats fictional (instant fills, points-only PnL, no fees), NWOG/Judas
dead. Backtested retroactively as the `legacy` variant: −45.1 %/60d.

---

## Current defaults that matter (v0.4)

| Param | Value | Why |
|---|---|---|
| `ENTRY_MODE` | 5m (+ ATR switch, low=0.8) | rulebook: 5m default for crypto |
| `FIB_VALIDITY_MODE` | structural | legacy = zero trades possible |
| `ENFORCE_TIER_RR` | true (off in benchmark runs) | documented design vs starvation |
| `TREND_ALIGNMENT_FILTER` | true | counter-trend longs = all March losses |
| `MIN_TP_DISTANCE_PCT` | 0.25 | TP must clear ~3× round-trip cost |
| `STOP_BUFFER_PCT` | 0.1 | %-of-price, not points |
| `VWAP_ENABLED` | true (recommend false) | fee-structural loser as parameterized |
| `NWOG_BIAS_OVERRIDE` | false | measured zero effect; up-gap risk |
| fees | 0.055/0.02/0.01 % slip | Bybit non-VIP |

## Backlog

- [ ] v0.4 validation result → log here, decide TP floor 0.25 vs 0.15
- [ ] Walk-forward split + trial counter in `run_backtest.py` (DSR/PBO gates)
- [ ] Live order lifecycle: TTL/cancel-on-invalidation for GTC limits
- [ ] VWAP redesign (higher TF, wider bands, jump/news conditioning) or removal
- [ ] 50+ trade sample before any live capital (rulebook rule)
