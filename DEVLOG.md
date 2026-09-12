# DEVLOG — Powell Trades Bot

## v0.19-exp — "First 5-min candle vs 12-EMA, trailing stop" (QuantLab reel, 2026-09-12)

Source: IG reel (fetched + Whisper-transcribed; frames read). Stated
rule: at the NY open, if the first 5-minute candle closes above the
12-EMA go long, below go short; the algo "trails the stop as momentum
develops and stays in the move as long as the momentum continues".
Claimed: NAS100 5m 2019-2026, 1,448 trades, 57 % win, PF 1.29, maxDD
just under 20 %, total return "982 %" (voiceover) / "+553 %" (on-screen
card — the reel contradicts itself); equity curve on screen is almost
entirely 2024-2026. Frames: 12-EMA on the M5 close; initial stop below
the signal candle's low; trailing stop steps up with the 12-EMA.
Family: ORB cousin (v0.16b) with an EMA direction filter and a trail.

**Mechanized primary (fixed BEFORE running), NAS100 1m→5m 2015-2020:**
- EMA12 on the continuous 5m close series (24 h CFD chart, as shown).
- Signal candle = the 5m bar starting 09:30 NY; close > EMA12 → LONG,
  close < EMA12 → SHORT, equal → skip. Entry at the 09:35 bar open
  (taker + slip).
- Initial stop = signal candle's opposite extreme (no buffer stated).
  From the next bar on, stop ratchets to the last CLOSED bar's EMA12
  when that is tighter (never loosens); intrabar stop-first; no target;
  flat at the 16:00 close. One trade per day, no re-entry.
- 1 % risk on the initial stop distance, 4× cap (as v0.16b); house
  futures-CFD costs (0.002 % + 0.005 % per side, both legs). Explore
  2015-2017 / holdout 2018-2020-05. Era caveat on record: the reel's
  window (2019-2026) overlaps ours only in 2019-2020-05, and its curve
  is back-loaded to 2024-26 — this test can falsify the rule's
  robustness, not its 2024-26 claim.
- **Pass:** explore n ≥ 100 ∧ net > 0 → holdout; holdout PASS = net > 0
  ∧ PF ≥ 1.10 ∧ maxDD < 40 %; a pass then faces the 2× cost stress
  (the v0.16c lesson). Reported either way against the reel's claimed
  57 % / PF 1.29 / DD < 20 %. Untested boundaries: a stop buffer, trail
  activation only after +1R, chandelier (ATR) trail instead of the EMA,
  holding through the trail overnight.

**Results (2026-09-12): passes the holdout bar at base costs — the
first reel to do so — then FAILS the pre-registered 2× cost stress.
Retired at retail costs, same signature as the published ORB.**

| costs | window | n | win % | PF | net | maxDD | exit mix (trail/stop) | cost/R |
|---|---|---|---|---|---|---|---|---|
| 1× | explore 15-17 | 772 | 29.5 | 1.12 | +$2,730 | 18.7 % | 70 / 30 | 0.15 |
| 1× | holdout 18-20 | 607 | 30.0 | **1.19** | **+$3,959** | 18.1 % | 76 / 24 | 0.10 |
| 2× | explore 15-17 | 773 | 26.5 | 0.87 | −$2,759 | 36.2 % | 70 / 30 | 0.31 |
| 2× | holdout 18-20 | 607 | 27.7 | 0.96 | −$741 | 25.2 % | 76 / 24 | 0.18 |

Explore gate met (n=772, net > 0); holdout PASS on every criterion
(net > 0, PF 1.19 ≥ 1.10, maxDD 18.1 % < 40 %). Then the stress:
negative at 2× on both windows; break-even ≈ 1.5× (explore) / 1.8×
(holdout) of base costs — inside the cost model's own uncertainty, the
v0.16c pattern exactly.

Against the reel's claims: our maxDD (18 %) matches its "just under
20 %"; our PF 1.12-1.19 sits below its 1.29; our win rate (30 %) is
nowhere near its 57 % — the EMA-ratchet trail takes many small trail
exits and lets the few trend days pay, so the win rate depends entirely
on the unstated trail mechanics. Regime concentration is severe:
holdout profit is 2019 alone (+$4,697 of +$3,959; 2018 flat, 2020
negative), explore profit is 2016 alone. The reel's own curve is
back-loaded to 2024-26 and its two headline numbers (982 % spoken,
+553 % on screen) disagree.

Reading: the ORB family on NASDAQ keeps producing the same object — a
small, real, regime-concentrated edge (PF ~1.1-1.2 at optimistic costs)
that disappears inside realistic execution. Three independent
constructions now (Z&A base, Z&A ATR, this EMA-trail) land in the same
place. That is the family's honest ceiling at retail costs.

## v0.18-exp — Funding carry: plain, timed, leveraged, rotated (2026-09-12)

New family, the first here where the income is MECHANICAL: hold spot,
short the perp of the same coin, collect funding every 8 h; price risk
is hedged, so the P&L is funding received minus basis drift minus
costs. Data: Binance archive — funding (all cells), monthly 1d spot and
USDT-M perp klines for the basis at rebalance points. Universe for the
rotation cell: 12 large caps with continuous history from 2021 (BTC,
ETH, BNB, XRP, ADA, DOGE, SOL, DOT, LINK, LTC, AVAX, ATOM). SURVIVORSHIP
NOTE on record: chosen by today's caps ⇒ biased toward coins that
survived; carry is delta-neutral so this affects which coins were held,
not price P&L, but delisted coins could have had basis collapses —
treated as an upward bias on the rotation cell.

**Cells (pre-registered, no grid):**
1. Plain: BTC and ETH carry, always on, 1× notional — the boring
   baseline.
2. Timed: in only while the trailing 24 h mean funding > 0, else flat.
3. Leveraged: cell 2 at 2× and 3× notional/capital (funding scales,
   basis and cost drag scale; margin/liquidation modeled as a cap, not
   simulated — stated).
4. Rotated: weekly (Monday 00:00 UTC) rebalance into the top-3 coins by
   trailing 7-day mean funding, requiring > 0; equal weight; positions
   held while the coin stays top-5 (hysteresis); basis P&L from 1d
   closes at entry/exit.

**P&L model:** daily funding = Σ settlements × rate × notional (shorts
RECEIVE positive funding); basis P&L = −Δ(perp/spot − 1) × notional
over the holding period; costs per replaced slot = spot 0.1 % + perp
0.055 % per leg, entry and exit (0.31 % round trip). **Reported:**
annualized return on notional, per-year, maxDD, worst month, share of
days flat, turnover. **Pre-stated expectation:** cell 1 ≈ +8-12 %/yr
BTC, +10-14 % ETH; cell 4 higher but with real basis and turnover drag.
**Pass bar for taking any cell further:** every year ≥ 0 on the
funding-covered window AND maxDD < 10 % at 1× (carry that draws down
like a directional trade is not carry). Exchange/counterparty risk is
outside the model and on record.

**Results (2026-09-12): the BORING cell passes; the not-boring cells
don't beat it.**

| cell | ann % on notional | CAGR | Sharpe | maxDD | worst month | years ≥ 0 | bar |
|---|---|---|---|---|---|---|---|
| 1 plain BTC | +11.6 | 12.3 | 8.54 | 2.3 % | −0.8 % | 7/7 | **PASS** |
| 1 plain ETH | +13.6 | 14.6 | 7.54 | 1.8 % | −1.5 % | 7/7 | **PASS** |
| 2 timed BTC | +5.6 | 5.8 | 3.26 | 7.7 % | −2.3 % | 5/7 | FAIL |
| 2 timed ETH | +7.8 | 8.1 | 3.71 | 12.7 % | −2.2 % | 4/7 | FAIL |
| 3 timed ETH 3× | +23.3 | 26.0 | 3.71 | 33.4 % | −6.5 % | 4/7 | FAIL |
| 4 rotated top-3 | +12.4 | 13.2 | 4.95 | 2.5 % | −0.6 % | 6/7 (2026 −1.2 % partial) | marginal |

Per-coin plain: LTC +14.6 % (DD 1.2 %), XRP +14.2, LINK +13.6, ADA
+13.3, DOGE +12.4, ATOM +9.4, DOT +7.5, AVAX +6.4 — and BNB −0.2 %
(DD 27 %), **SOL −2.8 % with a −25 % hedged DAY on 2022-11-10** (FTX
collapse: SOL perp had traded 17 % below spot; the basis snapped back
while funding charged shorts ~0.5 %/day). Verified as real data, not a
glitch. BTC's worst hedged day in 6.7 years: −0.7 % (2020-03-13).

Findings: (1) **timing hurts** — a sign-based funding timer whipsaws
around zero and pays 0.31 % per flip; plain carry beats it in every
coin. (2) **Rotation ≈ plain** — 12.4 % vs 11.6-14.6 % for the good
single coins, with 82 slot changes/yr and a survivorship-biased
universe; it did sidestep SOL/BNB, which is its one real merit.
(3) **Leverage scales the drawdown linearly** — 3× on the timed cell
turns a 12.7 % DD into 33 %; on the plain series 3× would be ~35 %/yr
at ~7 % DD ARITHMETICALLY, but in practice leverage on carry means
either borrowed spot (interest ≈ funding, no free lunch) or an
under-collateralized short leg that liquidates in a +30 % day — the
cap, not a knob. (4) Sharpe 7-8 is the daily-mark Sharpe of a nearly
deterministic income stream; it does not see intraday liquidation risk
on the short leg, exchange/counterparty risk (FTX), or basis
dislocations like SOL's — all outside the model and on record.

Verdict: BTC/ETH (and LTC/ADA/XRP/LINK/DOGE) plain cash-and-carry is
the first strategy in this project to pass a pre-registered bar with
no artifact suspected (audited: real basis from prices, costs charged,
worst days traced to real events). Honest expectation: **~10-14 %/yr on
capital at ~1× (spot notional + perp margin), Sharpe high, tail risks
exchange and liquidation**. It is the crypto version of the risk-free
rate — exactly what "boring" means, and exactly what the reels never
mention. Not adopted into the bot (needs spot + perp legs and margin
management — a different execution build); documented as the project's
first genuine, if modest, positive result.

## v0.10i — Re-entry semantics audit of the reference engine (2026-09-12)

Triggered by v0.10h's implausible result (Rule A: Sharpe 3-4 across
seven markets from a parameter-free filter). Suspected mechanism: the
frozen reference (recovered verbatim from the original validation
script) re-enters after an exit INSIDE bar i at bar i's OPEN — a price
from before the exit move. After-loss re-entries are therefore priced
pre-adverse-move (unrealistically bad), after-win re-entries
pre-favorable-move (unrealistically good). That is the exact shape of
the v0.10g streak numbers (32 % after one loss / 69 % after a win), and
Rule A would "work" by deleting the artifact's losers while keeping its
winners. The two biases partially cancel in the aggregate, so the
validated 58 % could be too high, too low, or about right — unknown
until measured.

Engine change: `simulate(..., reentry="open"|"exit"|"next")`. "open" =
the frozen reference (default, unchanged, still reproduces the
validation exactly). "exit" = same-bar re-entry filled at the exit
price (post-move; closest to the live bot, which re-enters at the
current mark after a stop). "next" = no same-bar re-entry (earliest
entry the next bar's open; fully realizable, conservative). Driver
`backtest/reentry_audit.py` loads each of the seven datasets once and
runs {open, exit, next} × {Rule A off, on}. Pre-stated reading: the
truth lies between "exit" and "next"; Rule A is real only if it still
improves PF/maxDD under BOTH realistic modes on the untouched markets.
The live bot is unaffected (it already re-enters at post-move prices);
only the backtest yardstick is.

**Results (2026-09-12): THE VALIDATED EDGE WAS THE ARTIFACT. v0.10c is
NOT validated; the v0.10d/e/f/g/h evidence is retracted.**

| dataset | reference "open" win/PF/Sharpe | "exit" (≈ live bot) | "next" |
|---|---|---|---|
| BTC 2019-22 | 58.0 / 1.18 / 1.68 | 52.7 / 0.99 / 0.01 | 53.5 / 1.03 / 0.35 |
| BTC 2023-26 | 57.5 / 1.14 / 1.22 | 51.9 / 0.92 / −0.77 | 51.5 / 0.92 / −0.70 |
| ETH 2018-26 | 57.5 / 1.15 / 1.66 | 52.8 / 1.00 / 0.16 | 52.2 / 0.99 / 0.01 |
| NAS100 15-20 | 54.0 / 1.12 / 0.97 | 51.2 / 0.99 / −0.01 | 51.1 / 0.99 / 0.03 |
| XAU 06-20 | 55.7 / 1.15 / 1.54 | 51.5 / 1.01 / 0.21 | 51.7 / 1.02 / 0.25 |
| WTICO 05-20 | 55.7 / 1.23 / 1.84 | 51.8 / 1.04 / 0.49 | 51.6 / 1.03 / 0.40 |
| SPX500 05-20 | 53.4 / 1.09 / 0.74 | 49.7 / 0.92 / −0.68 | 48.9 / 0.88 / −0.86 |

Rule A under realistic re-entry: PF 0.89-1.05, Sharpe −0.77 to +0.48 —
no improvement anywhere. The v0.10g streak effect was the artifact.

Mechanism, now certain: exit-then-entry in the same iteration filled
every same-bar re-entry at o[i] after an exit that happened LATER inside
bar i. After a target hit the re-entry was priced before a favorable
move the market had already made (a free head start — 69 % wins on
those trades); after a stop, before an adverse move (32 %). The
favorable side dominated: the aggregate "58 %" was ~52 % of real
continuation plus ~6 points of lookahead. The "family signature" across
six markets was the ENGINE's signature — a mechanical effect replicates
everywhere at the same magnitude, and that uniformity should have been
the tell (CLAUDE.md rule added).

Artifact-free read of the rule: 1H extension continuation with a
symmetric 3×ATR bracket wins ~51-53 % — a small, real continuation
tendency, consistent with the intraday-momentum literature — at
PF 0.92-1.04: roughly breakeven at retail costs, negative after
funding. NOT tradeable.

Scope of the retraction: only the bracket family (v0.10c reference,
v0.10d cross-market, v0.10e funding, v0.10f ETH, v0.10g/h streak) used
the same-bar re-entry ordering. Every reel/ICT engine fills entries at
the NEXT bar's open (or at a touched level) after signals from closed
bars and has no such path — the v0.12-v0.17 failure verdicts stand. The
live module never had the artifact (it re-enters at the current mark):
the paper bot's true expectation is the "exit" column — ~52 %, PF ~1.0
— and its 1-of-8 first week is consistent with exactly that.

Consequences: (1) v0.10c status → NOT VALIDATED, candidate retired;
(2) the go-live gates are VOID — no live money on this rule; (3) the
paper run may continue as a free live measurement with the target reset
(dashboard/stats text corrected); (4) docs/failure_path.md corrected —
the "survivor" section is withdrawn, the failure analysis of the reels
stands; (5) the project's validated-strategy count returns to ZERO.
Owned in full: the engine was reproduced faithfully to a flawed
original, exact reproduction was mistaken for validation, and
cross-market uniformity was read as robustness instead of as a
mechanical tell.

## v0.10g — Diagnostics: the reversed rule, and streak conditioning (2026-09-12)

User, after the 1-of-8 week: "can't we do the opposite on the same
signal?" Two fixed-rule diagnostics, pre-stated:
1. **Reverse cell** (`--reverse`): identical entries and symmetric
   3×ATR bracket, opposite side. Expected BEFORE running: with a
   symmetric bracket the reverse is the mirror image — win % ≈ 100 −
   ours − ambiguous-bar share, same costs — i.e. ≈ 40-42 % and deeply
   negative. Run on BTC 2019-22, BTC 2023-26, ETH 2018-26. If it were
   positive anywhere, the validated rule would be wrong there.
2. **Streak conditioning** on the validated trade sequences: win rate
   of the NEXT trade after 1, 2, 3, 4+ consecutive losses, and lag-1
   autocorrelation of outcomes. ≈ unconditional 58 % everywhere ⇒
   streaks carry no information ⇒ neither "flip after losses" nor
   "pause after losses" can help; a lower conditional rate ⇒ streaky
   (pausing could help); a higher one ⇒ mean-reverting (flipping is
   exactly wrong). No parameter changes; diagnostics only.

**Results (2026-09-12).**

1. **Reverse cell — catastrophic, exactly as computed.** BTC 2019-22:
41.4 % win, PF 0.58, −97 %, every year negative. BTC 2023-26: 42.0 %,
PF 0.60, −98 %. ETH 2018-26: 41.8 %, PF 0.63, −100 %. Win rates are
100 − 58 − ~0.5 % ambiguous bars: the mirror image. This is the
strongest possible confirmation that the signal carries real
information — an information-free signal would give ~50 % BOTH ways;
instead both directions are strongly asymmetric. Reference reproduction
re-verified exact before the cells ran.

2. **Streak conditioning — a real, triple-replicated effect.**
Win rate of the next trade, by consecutive losses immediately before it:

| dataset | base | after ≥1 L | after ≥2 L | after ≥3 L | after ≥4 L | lag-1 autocorr |
|---|---|---|---|---|---|---|
| BTC 2019-22 | 58.0 | 42.1 (n=632) | 49.2 | 53.2 | 60.9 (n=87) | +0.275 |
| BTC 2023-26 | 57.5 | 41.9 (n=689) | 49.8 | 52.7 | 60.0 (n=95) | +0.270 |
| ETH 2018-26 | 57.5 | 40.6 (n=1504) | 46.0 | 48.4 | 50.6 (n=247) | +0.294 |

Derived: the trade immediately after EXACTLY one loss wins ~32 % (BTC
2019-22: 86/266); trades after a win (or first) win ~69 %. The effect
is concentrated on the immediate re-entry after a fresh stop-out and
fades with streak length — mechanism: the rule re-enters at once in the
same whipsaw that just stopped it (this is exactly what the paper run
did on Sep 11: four stops in three hours). Outcomes are streaky
(autocorr ≈ +0.28) because regimes persist. Implications: "flip after
a loss" is exactly wrong (the reverse cell); "skip the immediate
re-entry after a loss" is the natural, PARAMETER-FREE candidate.

## v0.10h-exp — Pre-registered: one-signal cooldown after a loss (2026-09-12)

Candidate rule change to v0.10c, discovered post hoc in v0.10g and
therefore IN-SAMPLE on BTC and ETH. **Rule A:** after a losing trade,
the next qualifying entry signal is skipped (one signal), then normal.
No parameters. Everything else verbatim.

**Validation data — untouched by the streak analysis:** the four
v0.10d cross-market cells (NAS100 2015-20, XAU/WTICO/SPX500 2005-20,
futures-CFD costs). BTC/ETH filtered runs are reported as in-sample
magnitude only. **Pre-registered PASS:** in ≥ 3 of the 4 untouched
markets, filtered PF > unfiltered PF AND filtered maxDD ≤ unfiltered
maxDD AND filtered net > 0, with filtered trade count ≥ 50 % of the
original. PASS ⇒ Rule A becomes a candidate for the LIVE rule with its
own pre-registration for the switch (paper run continues unchanged
until then). FAIL ⇒ the streak effect is crypto-specific or a
same-bar-re-entry artifact; reported, not adopted.

**Results (2026-09-12): superficially PASS 4/4 under the reference
engine (NAS100 PF 1.12→1.50, XAU 1.15→1.44, WTICO 1.23→1.67, SPX500
1.09→1.51; Sharpe 2.7-3.9; maxDD roughly halved; BTC/ETH in-sample
similar) — a result so uniform it triggered the v0.10i engine audit,
which RETRACTS it: under realistic re-entry semantics Rule A improves
nothing (PF 0.89-1.05). The "improvement" was the removal of the
engine's stale-price after-loss re-entries while keeping its stale-price
after-win ones. Not adopted.**

## Paper run — week-1 audit after a 1-of-8 start (2026-09-12)

Dashboard after the first week: 8 closed, 1 win, −$661 (−6.6 %), two
shorts open. Two checks before drawing any conclusion:

**Calibration against the strategy's own history.** Binomial
P(≤1 win in 8 | 58 %) = 1.2 % (1 in 86) — but losses CLUSTER in chop,
so the backtest itself produces ≤1-win 8-trade windows 2.1 % of the
time (validation era, 31/1,501 windows) and 2.3 % (demo era). Longest
losing streak in BOTH eras: 7 (live so far: 4). Worst 8-trade stretch
≈ −8 % of equity (live: −6.6 %). The start is inside the validated
distribution, not at its edge.

**Mechanical audit.** Replayed Sep 8-11 BTC 1H candles (Binance
archive, monthly Aug + daily Sep files) through the frozen reference
engine. Every live trade maps to a rule trade: entries within
$40-200 (Bybit/Binance basis + sub-minute timing), the open short's
stop within $6 of the replay's (79,828.61 vs 79,834.54); the two
divergences (a second Sep-10 win the rule took, a Sep-11 07:00 short
it took) are explained by one-position-at-a-time given the live fill
being ~$200 lower on the Sep-10 short. The reference engine ALSO loses
the week: 9 trades, 2 wins, ≈ −$680. Verdict: regime, not malfunction —
BTC whipsawed 76.5k-80k with 1H ATR ~$700-1,000, firing extension
signals at both ends of a 3 % chop; that is this strategy's known
worst regime, and it is priced into the validation.

Nothing changes (per protocol: no goalpost moves). Pre-set checkpoints
stand: at 50 trades win % < 45 → deeper investigation; at 100 trades
win % < 50 or net < 0 → Gate 1 fails. Added
scripts/audit_paper_vs_rule.py to repeat this replay any week.

## v0.10f — ETH validation of the bracket rule (2026-09-12)

Purpose: a third GENUINE Bybit symbol for the paper run (XAUT is a
proxy), and the first fully clean crypto cell beyond BTC. Rule under
test: v0.10c VERBATIM — zero free parameters. Data: Binance public
archive (reachable; the funding source), spot ETHUSDT 1m monthly klines
2017-08 → 2026-08 (spot price series, matching the BTC methodology which
used Bitstamp spot), fetched + converted by backtest/fetch_binance_
archive.py; um-perp ETHUSDT funding 2019-11 → 2026-08 for the funding
gate. Caches: local/ethusd_1m_2017_2026.csv.gz (gitignored, regenerable
by script) and funding_ethusdt_binance.csv (committed). Saved artifacts
validated by re-loading through the consumers' own loaders (CLAUDE.md
rule). Known archive gotcha handled explicitly: spot kline timestamps
switched from ms to µs in 2025 files.

**Pre-registered BEFORE any run.** Windows: full 2018-01 → 2026-08
unfunded (2017 partial dropped), per-year breakdown; 2020-01 → 2026-08
unfunded vs funded on identical bars (Gate-2 style). Bybit retail costs
0.055 % + 0.01 %, 1 % risk, 10× cap. **PASS = the v0.10c validation bar
applied to ETH:** net > 0 ∧ win % ≥ 52 ∧ at least one bull year AND one
bear year individually net-positive, AND the funded 2020-2026 window
keeps net > 0 ∧ PF ≥ 1.10. PASS → ETHUSDT joins EMA_BRACKET_SYMBOLS on
the VPS (3 genuine symbols ⇒ ~3 trades/day). FAIL → reported; the edge
is then BTC-specific within crypto and the paper run stays as is. No
parameter changes in response to results.

**Results (2026-09-12): PASS on every pre-registered criterion — ETHUSDT
joins the paper run.**

| window | n | win % | PF | Sharpe | CAGR | maxDD | years + |
|---|---|---|---|---|---|---|---|
| 2018-01→2026-08 unfunded | 3,545 | **57.5** | 1.15 | 1.66 | 50.5 % | 35.5 % | 8/9 |
| 2020-01→2026-08 unfunded | 2,735 | 57.0 | 1.14 | 1.46 | 42.2 % | 35.5 % | 6/7 |
| 2020-01→2026-08 **funded** | 2,735 | 57.0 | **1.14** | 1.39 | 39.4 % | 35.4 % | 6/7 |

Bar: net > 0 ✓; win ≥ 52 % ✓ (57.5); bull year positive ✓ (2021
+$54.1k); bear year positive ✓ (2018 +$8.5k, 2022 +$46.6k); funded
window net > 0 ∧ PF ≥ 1.10 ✓ (PF 1.14). Both sides carry (longs
+$182k / shorts +$148k full window). The one negative year is 2023
(−$21.0k, ≈ −16 % of equity at the time). Funding costs 14 % of profit
over 2020-26 (longs −$5,443, shorts +$1,928; ETH funding averages
+13.9 %/yr vs BTC's +11.8 %) — CAGR 42.2 → 39.4, win rate untouched,
same shape as the BTC funding gate.

This is the first fully CLEAN crypto cell beyond BTC (data never
touched by any experiment) and the sixth market to print the family's
signature: win rates 53-58 % everywhere (BTC 58, ETH 57.5, XAU 55.7,
WTI 55.7, NAS 54, SPX 53.4) with the 3×ATR bracket.

Caveats on record: (1) ETH's ride is rougher than BTC's — maxDD 35.5 %
vs 15.6-22 %, worst month −12.6 % vs −7.6 %; (2) BTC and ETH are highly
correlated (~0.8), so BTC+ETH concurrent positions diversify less than
the headline "two symbols" suggests — worst-case open risk with three
symbols is 3 × 1 %, and two of those legs tend to move together;
(3) spot price series stands in for the perp (basis negligible),
Binance funding stands in for Bybit funding (venues arbitraged);
(4) raw compounded dollars are 1 %-compounding artifacts — quote
PF/Sharpe/CAGR. Action: `EMA_BRACKET_SYMBOLS=BTCUSDT,XAUTUSDT,ETHUSDT`
on the VPS → ~3 trades/day; Gate 1 clock roughly 5 weeks to 100 trades.

## docs — The failure path (2026-09-12)

User: "all the fails follow one exact path — identify it and eliminate
it." Compiled `docs/failure_path.md` from the ledger: every failed reel
/ ICT strategy (12 mechanizations, 4 markets) shares one construction —
draw a level, wait for a touch, enter at it, stop beyond the wick,
target a multiple — which yields two independent fatal properties:
(A) location ≠ information (observed win rates sit on each bracket's
random-walk null; v0.17 is below it), and (B) stops below the cost
floor (cost/R 0.2-1.0 vs 0.05 for the survivor). v0.10c is the
step-for-step inverse (state not level, enter with the move, 3×ATR
stop, symmetric bracket, no session gate) and is the only pass. The
doc ends with a five-question screen to apply BEFORE mechanizing
anything new. Eliminating the path = never building on it again; the
screen is the mechanism.

## v0.17-exp — Fixed-range volume-profile POC pullback (IG reel, 2026-09-12)

Source: @tradinglabofficial reel (fetched + Whisper-transcribed
in-house; 78 s). Stated rule: put a fixed-range volume profile over a
trend (low → high), enable VAH/VAL; wait for price to pull back to the
POC ("this is where we look to enter", ideally with a demand area
there); stop below the demand area; partial at VAH; full exit at the
recent high. Downtrend mirrored. Needs REAL volume → BTC 1H (Bitstamp
volume); index CFD data only has tick counts.

**Mechanized primary (fixed BEFORE running):**
- Swings: swing high = highest high of ±K=12 bars (confirmed K bars
  later — no lookahead); swing low mirrored. A trend = the last
  confirmed swing low followed by a confirmed swing high with impulse
  ≥ 3×ATR14 (shorts mirrored). Setup arms when the high confirms.
- Profile over the impulse bars: 40 price bins across the impulse
  range; each bar's volume spread uniformly over the bins its high-low
  range overlaps. POC = max-volume bin center. Value area = 70 % of
  volume expanded from the POC (larger neighbor first); VAH/VAL = its
  edges.
- Entry (long): resting limit at the POC while the setup is live; live
  = price between POC and the swing high at arming (if already below
  the POC, skip — the pullback is spent), no new high (a new high
  cancels; the next confirmed swing re-arms), max 100 bars. Gap-through
  fills at the bar open.
- Stop = VAL − 0.1×ATR; skip degenerate setups (fill − stop < 0.2×ATR,
  VAH not above fill). TP1 = VAH on half the position, TP2 = the swing
  high on the rest; stop unchanged after TP1 (nothing else stated).
  Stop-first conservative, no same-bar targets on the fill bar, one
  position at a time, no session gating (24/7).
- Costs: limit entry and TP legs at maker 0.02 %, stop at taker
  0.055 % + 0.01 % slip (the house limit-fill model). 1 % risk, 10× cap.
- Split: explore 2023-01→2026-08, holdout 2019-2022 (same consumed-era
  caveat as v0.15). **Pass:** explore n ≥ 100 ∧ net > 0 → holdout;
  holdout PASS = net > 0 ∧ PF ≥ 1.10 ∧ maxDD < 40 %. Reported either
  way; no variations in response to results. Untested boundaries:
  "demand area" as drawn (discretionary), other K/bin/value-area
  settings, HTF trend filters.

**Results (2026-09-12): FAIL — explore gate not met; holdout negative
too. First failure in the project NOT attributable to costs.**
- Explore 2023-2026: n=337, 35.6 % win, PF 0.78, −$4,071, maxDD
  44.5 %, 1.8 trades/week; 3 of 4 years negative; longs −$1,737,
  shorts −$2,335. Exit mix 191 STOP / 108 full win / 38 partial-then-
  stop. 752 confirmed setups skipped as "spent" (price already past the
  POC when the swing confirmed), 34 degenerate.
- Holdout 2019-2022 (for the record): n=455, 38.9 %, PF 0.86, −$3,132,
  maxDD 44.3 %; 2021 +$242 / 2022 −$32 flat, 2019-20 negative; longs
  −$2,753, shorts −$379.

Diagnosis: the stop is HEALTHY (1.1-1.7 % of price) and costs are
cheap (0.12-0.15 R) — the tight-stop law does not apply. The entry
itself loses: a pullback all the way to the POC is a pullback to the
BASE of the impulse (the POC sits in the pre-move consolidation), i.e.
a full retrace — which the data says is more often the start of a
reversal than a bounce. The reel equates "high-volume node" with
"support"; 792 trades across 8 years say it isn't, on BTC 1H. Also
structural: the picture in the reel (clean return to the POC after the
high) is the minority path — 752 of ~1,100 confirmed swings had
already blown through the POC by the time the swing was confirmable.
Untested boundaries as pre-registered (discretionary "demand area",
other K/bin settings, HTF filters) — none can repair a negative-
expectancy entry by construction.

## v0.16c — Cost stress test of the ORB ATR-stop cell (2026-09-12)

Next gate for the v0.16b Cell B candidate: its cost/R of 0.20-0.27 is
the highest of any positive result here, and the replication showed the
ORB family dies inside a normal spread. Pre-registered BEFORE running:
Cell B (5 % daily-ATR stop, EOD exit) re-run with ALL per-side costs
(taker 0.002 % + slip 0.005 %, entry-price slip included) multiplied by
**k ∈ {2, 3, 4}** — k=2 ≈ realistic NQ futures all-in (~1 index point
per side), k=3-4 ≈ index-CFD spreads at 9:35. Same data, same split,
zero strategy changes.

**Decision rule:** the candidate SURVIVES if at k=2 the explore window
stays net > 0 AND the holdout still meets its pass bar (net > 0 ∧
PF ≥ 1.10 ∧ maxDD < 40 %). k=3 and k=4 are reported as the CFD
scenario; the break-even multiplier is reported. A fail at k=2 retires
the candidate as an execution-quality artifact — no parameter rescue.

**Results (2026-09-12): FAIL at k=2 — candidate RETIRED as an
execution-quality artifact, exactly the replication's finding.**

| k | explore net / PF | holdout net / PF | cost/R (hold) |
|---|---|---|---|
| 1 (v0.16b) | +$2,149 / 1.10 | +$14,100 / 1.44 | 0.20 |
| 2 (≈ NQ all-in) | **−$2,352 / 0.88** | +$3,560 / 1.14 | 0.41 |
| 3 (≈ CFD) | −$5,600 / 0.69 | −$2,287 / 0.90 | 0.61 |
| 4 | −$7,430 / 0.56 | −$5,177 / 0.75 | 0.81 |

Decision rule required explore net > 0 AND holdout pass at k=2;
explore fails → retired, no parameter rescue (per pre-registration).
Break-even cost multiplier ≈ 1.5× (explore) / ≈ 2.6× (holdout): the
edge lives inside a band narrower than the uncertainty in the cost
model itself. Mechanism: a 0.06-0.09 %-of-price stop with a 10-12 %
win rate means the year is ~600 near-1R losses offset by a few dozen
trend days — every extra 0.007 % of per-side cost is charged on all
~600 losers and recovered on none. This is the paper's zero-slippage
assumption failing in the same way the independent replication showed
for the base cell (break-even inside QQQ's spread). Seventh instance of
the tight-stop law, and the cleanest: a genuine, literature-backed
signal that costs erase. Family status: ORB retired at retail costs;
only a venue with sub-0.005 %/side all-in execution could revisit it,
and that is not a retail venue.

## v0.16b-exp — The published ORB: Zarattini & Aziz (2023), both configurations (2026-09-12)

User: "try ATR-scaled stops and all the other things that make it
work." Rules verified from the paper's summaries (CXO Advisory,
therobusttrader) and an independent replication (giovannibrusco/
zarattini-2023-orb-qqq) rather than memory:
- Direction = body of the first 5-min bar (9:30-9:35): up → LONG,
  down → SHORT, doji → no trade. Entry at the 9:35 open.
- **Cell A (base QQQ case):** stop at the opening bar's opposite
  extreme (low for longs / high for shorts); target 10R; flat at 16:00.
  Paper: +675 % 2016-23, Sharpe ~1.06-1.12; ~75 % of trades stop out,
  ~22 % close flat, ~2-3 % reach 10R.
- **Cell B (TQQQ variant):** stop = 5 % of the 14-day ATR; no target;
  flat at 16:00.
- Sizing (both): min(1 % equity / R, 4× equity / entry) — the paper's
  Reg-T cap, not the house 10×. One trade per day. No re-entry.
- Paper costs: $0.0005/share commission, ZERO slippage. Replication:
  net PnL crosses zero at ~2.2¢/share slippage (≈ 0.007 % of a $300
  ETF — i.e. inside the quoted spread); 2022 alone = 38 % of PnL;
  portfolio-level edge over buy-and-hold "not established" (bootstrap
  CIs overlap). PRIOR ON RECORD: at our costs the base case is expected
  near break-even; Cell B's stop (~0.06 % of price) sits below the cost
  floor and is expected to fail the tight-stop law.

**Mechanization, NAS100 1m 2015-2020 (QQQ's underlying index):** first
bar = the five 1m bars 9:30-9:34 (open of 9:30, close of 9:34); doji =
|close−open| < 0.01 % of price. Entry = 9:35 bar open (taker + slip).
Session-daily ATR14 from 9:30-16:00 OHLC, shifted one day. Stop-first
conservative intrabar, no same-bar target on the entry bar, EOD flat at
the 16:00 close. House costs 0.002 % taker + 0.005 % slip per side, both
legs (harsher than the paper). Explore 2015-2017 / holdout 2018-2020-05.
**Pre-registered pass:** explore n ≥ 100 ∧ net > 0 → holdout; holdout
PASS = net > 0 ∧ PF ≥ 1.10 ∧ maxDD < 40 %. Reported either way; exit
mix and cost/R reported for comparison with the paper. Two cells = the
paper's two published configurations, not a grid.

**Results (2026-09-12): Cell A FAILS the explore gate; Cell B PASSES
the pre-registered holdout criteria — the first pass from any
reel-adjacent family. Status: candidate, NOT validated.**

| cell | window | n | win % | PF | net | maxDD | exit mix | cost/R |
|---|---|---|---|---|---|---|---|---|
| A base | explore 15-17 | 722 | 21.5 | 0.97 | −$875 | 38.5 % | 77/20/2.5 | 0.11 |
| A base | holdout 18-20 | 579 | 24.4 | 1.20 | +$10,467 | 24.8 % | 73/24/3 | 0.08 |
| B atr | explore 15-17 | 708 | 10.2 | 1.10 | +$2,149 | 28.1 % | 90/10/– | 0.27 |
| B atr | holdout 18-20 | 567 | 12.3 | **1.44** | **+$14,100** | 26.7 % | 88/12/– | 0.20 |

Cell A: explore net < 0 → gate not met; the positive holdout does not
count for adoption. Its per-year pattern (2015 −, 2016 +, 2017 −,
2018-20 +) is exactly the replication's "single-regime phenomenon".
Cell B: explore n=708 ∧ net > 0 → holdout unlocked; holdout net > 0 ∧
PF 1.44 ≥ 1.10 ∧ maxDD 26.7 % < 40 % → **PASS**. Every holdout year
positive (2018 +$5,354 / 2019 +$4,484 / 2020 +$4,262) across three
distinct regimes; shorts carry (+$10,993 vs longs +$3,107).

Mechanics on record: win rate 10-12 % — ~9 days in 10 stop out for
~−1R and the year is made by rare EOD trend days (winners average
~+8-13R). The 4× cap binds (stop ≈ 0.06-0.09 % of price ⇒ 1 % risk
would need ~11× notional), so realized risk is ~0.35 % of equity per
trade. Explore PF 1.10 is thin and 2016 alone carries it (2015/2017
negative) — regime concentration is real, but the holdout's three
positive years in three different regimes is the encouraging part.

**Why this is NOT validated yet (each is a required next gate):**
(1) **Slippage sensitivity** — cost/R 0.20-0.27 is the highest of any
positive result in this project; the replication found the base cell's
edge dies inside QQQ's own spread. Index-CFD spreads at 9:35 (~1-2
points ≈ 0.015-0.03 %) are 2-4× our modeled 0.007 %/side; futures (NQ)
costs are closer to the model. A pre-registered 2×/3× cost stress is
the immediate next step. (2) **Fresh-era validation** — this cache
(2015-2020-05) has been looked at by four families; the rules came from
the paper, not from this data, so the protocol is clean, but adoption
requires an untouched era (post-2020 NAS100 1m) exactly as v0.10c
required. (3) Trial count: 2 published cells + the v0.16 retest = 3
ORB-family cells; modest, on record. (4) Venue: the bot trades Bybit
(crypto); an index strategy needs a futures/CFD execution path — a
separate build.

## v0.16-exp — FCR breakout + retest, 1:3 (IG reel, 2026-09-12)

Source: user screenshots of an IG reel (diagram only, no transcript
needed). Rule as drawn: mark the High/Low of the first 5-minute candle
of the NY session (9:30-9:35 = "First Candle Range"); when price breaks
out of the range, wait for the 1m retest of the broken level; enter on
the retest with the stop just beyond the retest wick ("1" box) and the
target at 3× that distance ("3" box). Family context ON RECORD: opening-
range breakouts have real published evidence (Zarattini & Aziz 2023,
5-min ORB on QQQ) — the first reel family tested here with academic
support. The reel's retest entry + fixed 1:3 is a variant of that.

**Mechanized primary (fixed BEFORE running), NAS100 1m 2015-2020:**
- FCR = max high / min low of the five 1m bars 9:30-9:34 NY (all five
  required, else skip the day).
- Breakout: first 1m CLOSE outside the range, 9:35-10:29. Close above
  High → long bias; below Low → short bias. One attempt per day.
- Retest (short case; long mirrored): within 30 bars of the breakout,
  the first bar whose HIGH touches the Low (high ≥ Low) while its CLOSE
  stays below the Low. If any bar first CLOSES back inside the range,
  the breakout failed — no trade that day.
- Entry: next bar open after the retest bar (taker+slip). Stop = the
  retest bar's high (structure stop, no buffer — as drawn). Target =
  entry − 3 × (stop − entry). Skip if the fill is already beyond the
  stop. Stop-first conservative, no same-bar target on the entry bar,
  force-flat 16:00, max one trade per day.
- 1 % equity risk, 10× cap; futures-CFD costs (0.002 % taker + 0.005 %
  slip per side, both legs). Explore 2015-2017 / holdout 2018-2020-05
  (cache consumed by other families — taint note as before).
- **Pre-registered pass:** explore n ≥ 100 ∧ net > 0 → holdout;
  holdout PASS = net > 0 ∧ win % ≥ 27 (1:3 breakeven 25 % + costs) ∧
  maxDD < 40 %. Reported either way. Cost-to-risk ratio reported (the
  tight-stop law check). Untested boundaries: classic ORB entry on the
  breakout itself (the published version), 15m ranges, stops at range
  midpoint/opposite side, EOD-only exits — each would need its own
  pre-registration.

**Results (2026-09-12): FAIL — explore gate not met; both eras lose
every year.**
- Explore 2015-2017: n=341, **23.2 % win**, PF 0.67, −$3,929, maxDD
  42.4 %; longs and shorts both negative. Avg structure stop **0.051 %
  of price**; avg round-trip cost **0.72 R**.
- Holdout (for the record): n=274, 22.6 %, PF 0.75, −$3,253; every year
  negative. Avg stop 0.073 %; cost 0.35 R.

Two independent kill shots, either fatal alone: (1) **no entry
information** — the 1:3 bracket's random-walk null wins 25 %; the
retest entry prints 23.2/22.6 % across 615 trades and two eras (the
same "null minus costs" signature as v0.14/v0.14b/v0.15); (2) **the
drawn stop sits below the cost floor** — the "1" box is the retest
wick, ~5-7 index points, so fees+slip consume a third to three-quarters
of each R. Sixth confirmed instance of the tight-stop law. Note the
published ORB evidence (Zarattini & Aziz) uses ATR-scaled stops and
EOD exits — the reel's variant differs in exactly the dimension that
kills it. Classic ORB with ATR stops remains an untested, separately
pre-registerable boundary.

Patch note: first run of this engine shipped an inverted target
(`e - dr*RR*dist`) — every "TP" filled as −3R, 0 % wins. Caught from
the output's impossibility (TP exits with zero wins), fixed to
`e + dr*RR*dist`, bracket invariants now asserted at position creation,
CLAUDE.md rule added. The numbers above are from the corrected engine.

## v0.10e — Gate 2: real funding costs applied to the validated bracket (2026-09-11)

The go-live gate's biggest open question: perp funding was unmodeled in
every run. Data: Binance BTCUSDT USDT-M funding archive (Bybit's API is
unreachable from this environment; venue rates track via arbitrage —
proxy caveat on record). 7,305 settlements, 2020-01 → 2026-08, perfect
8h grid (00/08/16 UTC), mean +0.0108 %/8h ≈ +11.8 %/yr on notional,
86 % positive, 2021 avg +30.6 %/yr — the adverse-correlation risk
(momentum longs cluster in manias when funding peaks) is real in the
raw data. Committed: backtest/data_cache/funding_btcusdt_binance.csv.

**Application convention (fixed BEFORE running):** at each UTC-aligned
1H bar open matching a settlement, positions carried INTO the bar
accrue −dir × qty × open × rate (longs pay positive rates, shorts
receive). Accrual folds into that trade's net at close — win/loss
classification includes funding — and into mark-to-market equity. A
position entered at the settlement bar's own open pays nothing for that
settlement. Implemented as an OPTIONAL simulate() param defaulting to
None so the frozen reference behavior is unchanged (verified by exact
re-reproduction of the validation numbers).

**Windows:** 2020-01→2022-12 (funded validation window, 3 of 4
validation years) and 2023-01→2026-08 (demo era), each run funded vs
unfunded on identical bars. Reported: net/CAGR/PF/win % deltas, total
funding split by side (the correlation question), per-year.

**Pre-registered Gate-2 PASS: funded 2020-2022 stays net > 0 AND
PF ≥ 1.10.** No parameter changes in response to results; if it fails,
the next step is instrument analysis (quarterly futures / spot), not
tuning.

**Results (2026-09-11): GATE 2 PASS — funding shaves 4-12 % of profits;
the edge survives intact.**

- 2020-2022, identical bars: unfunded +$16,676 / PF 1.16 / CAGR 39.2 % /
  Sharpe 1.47 → funded **+$14,679 / PF 1.14 / CAGR 35.6 % / Sharpe
  1.37**. Win % unchanged (57.2), maxDD unchanged (15.6 %). Funding
  −$1,376 total: longs paid −$1,989, shorts COLLECTED +$623 — the
  two-sided book refunds ~⅓ of the long bill. Gate (net > 0 ∧
  PF ≥ 1.10): **PASS**.
- 2023-2026: +$18,820 → +$18,083 (−4 % of profit; CAGR 33.6 → 32.7).
  Funding −$394 (longs −$1,166, shorts +$763).
- The pre-identified adverse correlation is real but bounded: 2021
  (avg funding +30.6 %/yr) absorbs most of the drag (+$3,834 → +$2,758)
  and still ends positive. Win rate untouched in both windows — funding
  almost never flips a trade's sign; it is a thin shave on net, not a
  structural cost. The "halves the edge" scenario did not materialize.
- Go-live consequence: **Bybit perps stand as the venue** — no
  instrument switch; funding is now a measured, budgeted ~1-4 CAGR
  points. Reference reproduction re-verified exact (1,508 / 58.0 % /
  +$36,925) in the same batch before any funded cell ran.

Patch note: the first funded runs crashed — the committed funding CSV
was corrupt (`.astype(int64)` on ms-unit datetimes → epoch garbage;
every in-memory sanity check passed because corruption happened in the
final save line). Rebuilt via the save_cache_1m epoch idiom and
validated by re-loading the SAVED file through load_funding; CLAUDE.md
rule added (never astype(int64) datetimes; validate saved artifacts
through the consumer's loader).

## v0.13d — Web dashboard for the paper run (2026-09-10)

User wants to watch the forward test from a browser instead of SSH.
Added `scripts/dashboard.py` — stdlib-only HTTP server on the VPS
(port `DASHBOARD_PORT`, default 8080) rendering one read-only page:
equity + realized PnL + win rate vs the ~58 % target, realized equity
sparkline, per-symbol table, open positions, last 10 closed trades, and
a bot heartbeat from the bot.log mtime (alive/STALE). Auto-refresh 60 s.

Access control: refuses to start without `DASHBOARD_TOKEN` in .env;
requests must carry `?token=…` (constant-time compare, 403 otherwise).
Read-only by construction — renders only the paper CSV and log mtime;
no actions, no secrets on the page, no file access beyond those two.
Plain HTTP on record as acceptable for paper-money numbers.
`deploy/dashboard_setup.sh` generates the token, installs the
`powelltrades-dash` systemd unit, opens ufw if active, prints the URL.
Tested: 403 on bad token, 200 with content on good token, render-error
path never kills the server.

## v0.13c — Multi-symbol paper trading for the EMA bracket (2026-09-08)

User wants faster forward-test evidence ("im impatient — paper btc, oil
and gold"). Venue reality: Bybit has no oil in any form (would need an
OANDA/CFD integration — parked as roadmap); gold exists as tokenized
perps (XAUTUSDT / PAXGUSDT) tracking spot gold. Built multi-symbol
support: `EMA_BRACKET_SYMBOLS` (comma-sep, default BTCUSDT only); one
strategy instance + one position slot PER symbol; SHARED paper equity
(portfolio compounding; worst-case open risk = N × 1 %); symbol-scoped
paper resolution in orders.py (`check_paper_position`/`has_open_position`
take symbol — without this one market's price would resolve another's
bracket) and symbol-stamped CSV rows; per-symbol paper_stats. Smoke
replay with stubbed BTC+XAU feeds: independent trading, sane per-symbol
prices, correct shared equity.

Fidelity note ON RECORD: XAUTUSDT is a PROXY for the validated XAU cell
— 24/7 weekend sessions (validation data had none), thinner book,
different venue. Its results count as their own cell, not as the XAU
backtest's forward test. Doubling symbols ≈ halves calendar time to
~100 trades (~7-8 weeks); the per-market decay question still needs
per-market samples.

## v0.10d — Cross-market breadth check of the validated bracket (2026-09-08)

User: "can we test it cross market just in case." Rule under test:
v0.10c VERBATIM — zero free parameters, no grid, no tuning — so this is
a robustness measurement of a fixed rule, run full-period with per-year
breakdown (nothing to select ⇒ no explore/holdout machinery needed).

Markets (all 1H, futures-CFD costs 0.002 % taker + 0.005 % slip):
- **NAS100 2015-2020** — family-clean (no EMA-distance rule ever ran on
  this market; the cache served unrelated ICT/sweep families).
- **XAU, WTICO, SPX500 2005-2020** — entry-family-TAINTED: v0.10b ran
  EMA-distance entries (EMA-touch exit) on them and we know oil trended,
  gold was weak, SPX was dead. Diagnostics, not clean tests.

**Interpretation pre-stated BEFORE results:** the BTC validation stands
on its own (~3,100 trades, three windows, 57-58 % stable) REGARDLESS of
this outcome. Cross-market failure does not invalidate the BTC paper
run — the literature says intraday momentum is state/asset-dependent,
and v0.10b already showed 1H extension behavior differs by asset. What
this measures is whether the edge is BTC-specific or general. The
diagnostic is win % vs the ~50 % + costs breakeven of the symmetric
bracket: ≥ 53-54 % with positive net in a market = the effect travels;
~50 % = coin flip there; the BTC number changes in NEITHER case. No
parameter changes will be tried in response to results.

**Results (2026-09-08): THE EFFECT TRAVELS — all four markets clear the
pre-registered bar (win ≥ 53-54 % + net > 0).**

| market | n | win % | PF | Sharpe | maxDD | CAGR | years + |
|---|---|---|---|---|---|---|---|
| NAS100 15-20 (clean) | 2,126 | 54.0 | 1.12 | 0.97 | 25.8 % | 21.7 % | 5/6 |
| XAU 06-20 | 5,002 | 55.7 | 1.15 | 1.54 | 26.3 % | 37.5 % | 14/15 |
| WTICO 05-20 | 6,430 | 55.7 | 1.23 | 1.84 | 22.6 % | 50.2 % | 16/16 |
| SPX500 05-20 | 5,819 | 53.4 | 1.09 | 0.74 | 37.0 % | 14.6 % | 12/16 |

With BTC's ~3,100 trades at 57-58 %, the family now spans ~22,500
trades across five markets and four asset classes, every one above its
breakeven. Ordering matches the state-dependent-momentum literature:
crypto > energy/metal > indices. Notable: with the BRACKET exit even
SPX500 is weakly positive — v0.10b's EMA-touch exit had it dead
(PF 0.78-0.92); the exit is as load-bearing as the entry, consistent
with how v0.10c was discovered. The one negative NAS100 year (2015,
−17 %) and SPX's 2014-15 show regime dependence is real.

**Honest caveats, on record:** (1) XAU/WTICO/SPX are entry-family-
tainted cells (pre-noted) — though v0.10b's "SPX dead" verdict would
have discouraged this run, so the taint points conservative there;
NAS100 is the clean cell and passes. (2) Raw compounded dollars (oil
+$5.0M over 16y) are 1 %-compounding artifacts — quote PF/Sharpe/CAGR,
never the dollar figure. (3) CFD financing/roll costs unmodeled (same
caveat class as BTC perp funding) — matters most for oil. (4) Per
pre-registration: BTC validation and the live paper run are UNCHANGED;
no parameters were or will be touched from these results. The bot still
trades BTC only — cross-market execution would be a separate build.

## v0.13b — VPS deployment prep for the EMA-bracket paper run (2026-09-07)

Patch for the user's Vultr rollout: `BYBIT_TESTNET` is now env-driven
(default true). For the paper run set `BYBIT_TESTNET=false` so the feed
reads REAL mainnet market data via public endpoints — testnet candles
are thin fake-market data and would corrupt the forward test.
`PAPER_TRADE=true` never sends orders regardless, and with no API keys
in `.env` the account is untouchable by construction. Also:
`numpy` added to requirements.txt (imported directly by the strategy),
and `scripts/paper_stats.py` added — prints equity / win rate / open
position from logs/trades.csv for checking the forward test against the
validated ~58 % expectation.

## v0.15-exp — ComLucro "Three-Candle Liquidity Grab Reversal" (2026-09-07)

Source: YouTube p0rmH1VmNYQ ("Smart Money Liquidity Sweep Reversal
Strategy", ComLucro Trader, 16 min) — transcript pulled via the new
yt-dlp caption route (datacenter bot-check bypassed with a node JS
runtime + embedded player clients; manual EN subs).

Stated pattern (bullish; bearish mirrored): price sweeps a liquidity
level, then EITHER (2-candle) the sweep candle C2 takes C1's low and
closes back above C1's range, confirming immediately, OR (3-candle) C2
fails that close, and C3 holds above C2's low while closing above the
top of C2's body. Video demos on BTCUSD; execution shown with partials
at 1:1 (close half) and runner to 1:2.

**Mechanized primary (fixed BEFORE running):** BTC 1H. External-liquidity
context: the sweep must take out the prior 24-bar low/high (K=24 1H bars
ending before C1), not merely C1's wick. 2-candle confirm: l2 < l1,
l2 < K-bar low, close2 > high1. 3-candle confirm: l2 < l1, l2 < K-bar
low, NOT close2 > high1, then l3 >= l2 and close3 > max(open2, close2).
Enter next bar open (taker+slip); stop at the sweep extreme; TP1 = 1R
on HALF the position, TP2 = 2R on the rest; stop unchanged after TP1
(no breakeven move stated in the video). Stop-first conservative, no
same-bar targets on the entry bar, one position at a time, no session
gating (BTC 24/7). 1 % risk, 10x cap, 0.055 % taker + 0.01 % slip both
legs. Untested boundary, on record: the video's fib-50 %/premium-
discount limit entry, 15m CISD/ChoCh execution layer, and
POI-retracement (order block / FVG) context are NOT mechanized here —
only the swept-swing external-liquidity scenario the video also states.
**Split:** explore 2023-01 -> 2026 cache; holdout 2019-2022 (consumed
once, by the unrelated v0.10c validation — taint note on record).
**Pass:** explore n >= 100 AND net > 0 -> holdout; holdout PASS = net > 0
AND PF >= 1.1 AND maxDD < 40 %. Reported either way; no variations in
response to results.

## v0.14b-exp — Reactor's variant: DOL targets instead of fixed 1:2 (2026-09-07)

User-requested follow-up to v0.14 (its own pre-registration, per
policy). Identical spec to v0.14 in every respect except the target:
instead of fixed 1:2, target the NEAREST opposing session level beyond
entry ("target your next draw on liquidity") — for longs the nearest of
{Asia high, London high} above entry, for shorts the nearest of {Asia
low, London low} below; skip the trade if none exists on the profit
side. Stop stays at the sweep extreme. Same split, costs, risk, and
**pass bar** as v0.14 (win% bar replaced by PF >= 1.1 since RR is now
variable; avg realized RR reported). Caveat pre-stated: a target change
cannot add information to an entry shown to carry none — this tests
whether the PAYOFF map alone rescues the trigger.

**Results (2026-09-07): BOTH FAIL — and both land exactly on the
random-walk null, minus costs.**

v0.14b (DOL targets): explore n=1,397, 28.8 % win, avg NOMINAL RR 4.93,
PF 0.88, −$6,529, maxDD 68.9 %; holdout n=1,086, 27.1 %, avg RR 4.86,
PF 0.88, −$5,758. The nearest-opposing-level target sits ~5R away on
average; under a random walk P(win) ≈ 1/(1+RR) for ANY payoff map, so
EV stays 0 before costs no matter where the target goes — the win rate
moved from 32 % to 28 % in exact compensation. PF 0.78→0.88 = a change
of SHAPE, not of sign. Pre-stated caveat confirmed: a target cannot add
information to an information-free entry.

v0.15 (ComLucro 2C/3C grab, BTC 1H): explore n=831, 33.7 % win, PF
0.74, −$7,627, every year negative; holdout n=778, 34.6 %, PF 0.85,
−$4,949 (2019 flat, rest negative). Both pattern variants negative in
both eras. The null-match is surgical: TP1 (±1R) hit 49.6 % vs the
50 % coin-flip null; TP2-given-TP1 hit 68.0 % vs the 66.7 % null;
full-win rate 33.7/34.6 % vs the 33.3 % null. Across ~1,600 trades and
8 years, the sweep + candle-confirmation sequence shifts the odds by
approximately NOTHING; the account bleeds exactly the cost wedge.

Running tally of the sweep-reversal family: v0.14, v0.14b, v0.15 all
statistically indistinguishable from random entries. The only validated
strategy (v0.10c) is the opposite trade — extension CONTINUATION.
Untested boundary reiterated: ComLucro's fib-50 % limit entry and 15m
CISD/ChoCh execution layers (discretionary, not mechanizable as stated).

## v0.14-exp — Session-sweep 1m FVG reversal, "wake up at 9am NY" reel (2026-09-07)

Source: user-uploaded IG reaction reel (transcribed in-house via Whisper —
new capability; raw transcript stays out of the repo per policy). Stated
rule: at 9am NY, mark the Asia and London session highs/lows; when one
sweeps, drop to 1m and take a fair-value-gap reversal to the other side;
1:2 RR. Reactor adds: stop at the sweep swing. Home market per the
reactor's handle: NQ -> NAS100 1m cache (2015-2020).

**Mechanized spec (all decisions fixed BEFORE running):**
- Sessions (NY): Asia 18:00-02:00, London 02:00-08:00; levels frozen at
  09:00. Sweeps counted 09:00-11:59 only.
- Sweep: first 1m bar breaching an unused level (high above H / low
  below L). Opens a reversal context: direction against the sweep,
  anchor = running sweep extreme, expiry 30 bars. Same-side levels
  swept meanwhile are consumed; opposite-side sweeps ignored while a
  context is live. A bar sweeping BOTH sides voids both levels (skip).
- Entry: first 1m FVG against the sweep (3 closed candles, first candle
  no earlier than the sweep bar): bearish h[i] < l[i-2] after a high
  sweep, bullish l[i] > h[i-2] after a low sweep. Enter next bar open.
- Stop at the sweep extreme (no buffer, per the reel); target = fixed
  1:2 on the raw stop distance. Stop-first conservative, no same-bar
  target, gap-skip if the entry opens beyond the stop. Force-flat at
  16:00 NY. One position at a time; each level trades once per day.
- Risk 1% equity, 10x cap; futures-CFD costs (0.002% taker + 0.005%
  slip per side, both legs) — same as v0.9/v0.10b NQ tests.
- Split: explore 2015-08 -> 2017-12, holdout 2018-01 -> 2020-05. Taint
  note ON RECORD: this cache served v0.9 (ICT RB family) — different
  rule family, same market/era; a holdout pass here would still need a
  fresh-era check before adoption.
- **Pre-registered pass:** explore n >= 100 AND net > 0 -> holdout;
  holdout PASS = net > 0 AND win% >= 36 (1:2 breakeven 33.3% + costs)
  AND maxDD < 40%. Reported either way; no variations in response to
  results. The reactor's "target DOL instead of 1:2" variant is NOT
  tested unless the primary passes explore (would get its own prereg).

**Results (2026-09-07): FAIL — explore gate not met; both eras lose every
single year.**
- Explore 2015-2017: n=1,320, **32.0 % win**, PF 0.78, −$8,491, maxDD
  85.6 %, 1.21 trades/day; all four levels (AH/AL/LH/LL) negative.
- Holdout (printed for the record): n=1,030, **32.6 %**, PF 0.80,
  −$7,430; all four levels negative again. EOD force-flats rare (18/22)
  — not a distortion source.

Kill signature — the most instructive yet: for a 1:2 bracket the
RANDOM-WALK null wins exactly 33.3 % (gambler's ruin: target 2R away,
stop 1R away). The strategy prints 32.0/32.6 % across 2,350 trades in
two disjoint eras. The session-sweep + 1m-FVG-reversal trigger therefore
carries ~ZERO directional information on NQ — the loss is pure cost drag
(~0.06R/trade) on a coin flip. Unlike the tight-stop deaths (v0.8,
v0.12), the geometry here is survivable; the ENTRY is simply
uninformative. The reactor's "target DOL instead of 1:2" variant stays
untested per pre-registration (primary failed explore).

Capability note: this test ran end-to-end from a user-uploaded video —
in-house Whisper transcription + frame reads (new pipeline; raw
transcripts stay out of the repo per policy).

## v0.13 — v0.10c goes live: EMA-bracket paper trading wired into the bot (2026-09-03)

User: *"set up paper trading from validated strategy from before, the ema
200 trend following"* — the forward test the v0.10c validation earned.

**Reference recovered + committed.** The validation script was
scratchpad-only and a container restart wiped it. Its semantics were
recovered VERBATIM from the session transcript and committed as
`backtest/bracket_experiment.py`; reproduction on BTC 1H 2019-2022 is
exact to the dollar: 1,508 trades, 58.0 % win, +$36,925, maxDD 15.6 %,
Sharpe 1.68, per-year +6,101/+19,074/+6,744/+5,006, L/S
+21,669/+15,256. (A first reconstruction from the DEVLOG prose alone got
1,082 trades / +$3.3k — the prose under-specified three execution
details: the signal is the PREVIOUS bar's d entering at the current
bar's open; exits are checked before entries each bar, so no same-bar
exit and same-bar re-entry after an exit; exits fill at raw bracket
levels with taker+slip charged per leg. Recovering the code, not
re-deriving it, was the difference — CLAUDE.md rule added.)

**Live module:** `strategy/ema_bracket.py`, identical math; new config
`STRATEGY` (default **"ema_bracket"**; `ict_vwap` restores the old
pipeline) + `EMA_BRACKET_*` validated params. `main.py` runs a dedicated
loop: 60 s ticks, 1H×1000 fetch (EMA200 weight truncation ~0.005 %),
evaluate on the last CLOSED candle, one position at a time, RiskManager
sizing (same 1 %/10× formula), OrderManager paper CSV. ICT risk gates
(daily/weekly caps, killzones, re-entry budgets) deliberately BYPASSED —
they are not part of the validated rule; adding them would forward-test
a different strategy. Paper-only guard: refuses to start live.

**Parity proven:** `backtest/parity_ema_live.py` replays cached data
through the live module exactly as main.py drives it — 85/85 entries
identical to the reference, level diffs 0.0000000000. Run it after ANY
change to either file.

**Paper accounting upgraded (per the standing lesson):** CSV gains a
`qty` column; closed rows with qty book fee-aware $ PnL under the
validated cost model (raw-level exits, taker+slip per leg); paper equity
= start balance (+$10k default) + realized $ PnL, so sizing compounds
like the backtest. Legacy rows keep points-PnL. Smoke replay through the
real bot tick path: 26 trades, 60 % win, +$178.83, brackets resolving,
exclusivity holding.

**Bug found by the smoke test:** `check_paper_position` assigned float
pnl into the dtype=str frame — raises on pandas 2.x+ and aborted every
resolution pass (latent in the OLD code too, would have silently frozen
all paper monitoring). Fixed with string writes; CLAUDE.md lesson added.

**Live-vs-backtest gaps, on record:** (1) live brackets resolve on 60 s
mark-price ticks vs bar-level modeling without same-bar exits — live is
finer-grained, divergence expected small and unbiased; (2) windowed
live EMA vs expanding backtest EMA (~0.005 % weight); (3) perp FUNDING
still unmodeled — flagged at validation, must be revisited before any
live-money decision; (4) live qty rounds to 0.001 BTC.

**Run on the VPS:** `git pull`, then `python main.py` (PAPER_TRADE and
STRATEGY=ema_bracket are the defaults). Expect ~1 trade/day, ~58 % wins,
weeks of runtime before the sample says anything.

## v0.12e — The user's actual open: Asia / Globex daily open, 8am AEST (2026-09-03)

User clarified which "open" the taught setup trades: *"before asia opens,
when the market opens, 8am aest time"* — i.e. the CME Globex daily open,
18:00 NY (= 8:00 AEST under matching DST). Verified in-data: the 17:00 NY
hour carries only 25 % of normal 5m bars (daily halt) and 18:00 resumes
at ~97 % — the daily open exists in the Oanda XAU feed. None of the
v0.12d windows covered it. Anchor is fixed at 18:00 NY year-round (the
market open itself; its Sydney label drifts 8→10am with DST).

**Pre-registered BEFORE running:** windows {18:00–21:00 NY (3 h,
killzone-width, ≈ 8-11am AEST), 18:00–19:00 NY (literal first hour)} ×
geometries {`atr1_03`, `wick03`} = 4 cells, rejection trigger, same
split/costs/risk as v0.12c-d. Same rule: explore n ≥ 100 ∧ net > 0 →
holdout; holdout PASS = net > 0 ∧ win ≥ 77 % ∧ maxDD < 40 %. All cells
reported. Trial count on record: 10 session cells now tried on this rule
family. Diagnostic: does the Asia open beat the US floor session's
61.7/62.7 % (the best window so far)?

**Results (2026-09-03): FAIL — and the Asia open is the WORST window yet
tested for the wide-stop geometry.** Holdout win-rate ranking across all
five windows (`atr1_03`): US floor 62.7 % > London 60.0 > NY-AM 59.3 >
24 h baseline 59.2 > **Asia-open 3 h 55.5 % / first-hour 56.8 %** — the
taught window lands BELOW the unfiltered baseline. Cells:

- `atr1_03` 18-21: exp 54.1 % PF 0.30 −100 %; hold 55.5 % PF 0.29 −99.9 %
- `atr1_03` 18-19: exp 49.6 % PF 0.24 −95.9 %; hold 56.8 % PF 0.32 −88.8 %
- `wick03` 18-21: exp 46.4 % PF 0.30, hold 43.3 % PF 0.23; −100 %
- `wick03` 18-19: exp 46.6 % PF 0.25, hold 44.1 % PF 0.23; −91/−94 %

Reading: FVG continuation is a liquidity/participation effect — strongest
with US volume in the book (floor session), weakest in the thin Asia
open. Costs are also UNDERSTATED here: CFD/futures spreads at the 18:00
reopen run multiples of normal, so reality is worse than these numbers.
Window-definition note: a fixed 8am-Sydney clock would sit inside the
17:00 NY halt part of the year; "when the market opens" (18:00 NY
year-round) is the only tradeable reading and was used.

Verdict for the 80 % claim: the taught session is the setup's WEAKEST
window — session cannot be where the IRL 80 % comes from, strengthening
the v0.12c reconciliation (selection / sample size / counting). 10
session cells tried on this rule family; none explore-positive.

## v0.12d — Session filter: "only trade the open" (2026-09-03)

User hypothesis after v0.12c ("how about all trading open market"): the
missing discretionary filter might be session — trade the setup only
around the market open. Gold trades ~23 h/day so "the open" is ambiguous;
three canonical windows pre-registered (NY-local time) BEFORE any run:

- **London killzone 02:00–05:00** (ICT London open KZ)
- **NY AM killzone 07:00–10:00** (ICT NY open KZ)
- **US floor session 08:20–13:30** (COMEX gold pit hours — "when the US
  market is open" in the widest sense)

Grid: {`atr1_03`, `wick03`} × 3 windows = **6 explore cells**, rejection
trigger, same 2006-2012 / 2013-2020 split, same costs, 1 % risk. The
`--session` flag gates ENTRY ARMING only (the tap must occur in-window);
open positions manage to completion around the clock; gap
inventory/aging unchanged. No other knobs change.

**Pre-registered:** explore n ≥ 100 ∧ net > 0 → holdout; holdout PASS =
net > 0 ∧ win ≥ 77 % ∧ maxDD < 40 %. All 6 cells reported regardless.
Multiple-testing on record: 6 cells ⇒ ~1-2 lucky explore survivors
expected by chance; only holdout counts. Diagnostic of interest even on
FAIL: does win % move toward the 76.9 % breakeven bar in any window vs
the 24 h baselines (57.8/59.2 % `atr1_03`; 45.6/43.7 % `wick03`)?

**Results (2026-09-03): FAIL — all 6 cells net-negative in explore (no
survivor), −100 % in both eras everywhere. But the user's instinct is
directionally REAL:** the US floor session lifts `atr1_03` from the 24 h
baseline 57.8/59.2 % win to **61.7 % explore / 62.7 % holdout** —
consistent across both eras — with trade rate down to a human-scale
2.6-2.8/day. London (55.9/60.0) and NY-AM (57.4/59.3) add little.
`wick03` is session-insensitive (43.9-45.8 % everywhere): its losses come
from stop-to-noise distance, not time of day.

The remaining gap: at floor-session realized payoffs (+0.28R / −1.11R
incl. costs) breakeven is ~79.9 % win; achieved 62.7 %. Session filtering
recovers ~4 of the ~17 missing points; PF improves 0.36 → 0.43 — still
losing ~57 c per $1 risked; year-one bleed merely slows (−$8.4-8.6k vs
−$9.99k). Conclusion: "only trade the open" is a real effect ~4× too
small. The 80 % IRL claim cannot be reached by session choice alone;
remaining mechanizable candidates: HTF-trend gating, news-day exclusion.
Discretionary gap-quality and sample/counting artifacts (v0.12c) remain
the unfalsifiable residue.

Patch note: first 6-cell run crashed on the session gate
(`.to_numpy()` called on an ndarray — `df.index.hour` arithmetic already
yields ndarray); one-line coercion fix, full re-run, no logic change.

## v0.12c — The "80 % IRL" reconciliation: flipped-geometry readings (2026-09-03)

User challenged the v0.12/b FAIL: *"irl testing shows an 80 % win rate …
everything stated there is the exact set up."* Diagnosis before running
anything: 80 % wins is impossible for the tested geometry (stop 0.3×ATR /
target 1×ATR — breakeven 23.1 %) but is exactly the signature of the
FLIPPED reading of "0.3:1" — **risk 1 to make 0.3**, breakeven 76.9 %.
So the notation was treated as ambiguous and both honest completions of
the flipped reading were run: same rejection-wick trigger as v0.12b (wick
enters the 5m FVG, body closes outside, enter next open), same
2006-2012 / 2013-2020 split, no other changes. New `--geom` flag:

- `atr1_03` — stop 1×ATR14, target 0.3×ATR14.
- `wick03` — stop beyond the tap-candle wick + 0.05×ATR buffer (floored
  at 0.1×ATR), target 0.3× the risk distance — the structure-anchored
  version a teacher most plausibly means.

**Results (2026-09-03): FAIL — both geometries, both eras, −100 % in
year one.**

- `atr1_03`: explore n=31,961, **57.8 % win**, PF 0.36, avg +0.27R/−1.15R,
  −100 % inside 2006; holdout n=29,905, **59.2 % win**, PF 0.36, −100 %
  inside 2013. ~11-13 trades/day.
- `wick03`: explore n=32,402, 45.6 % win, PF 0.30, −100 % inside 2006;
  holdout n=30,304, 43.7 % win, PF 0.21, −100 % inside 2013.

The wide-stop version is the most "80 %-looking" of any reading — and it
tops out at **59.2 % against a 76.9 % breakeven bar**. All four readings
of "0.3:1" (two triggers × two geometries) are now tested and dead on
~14 years of gold 5m data, ~30k trades per era.

Reconciliation of the IRL 80 % (on record): (a) **small sample** —
P(≥16/20 wins) ≈ 5 % even when the true rate is 60 %; ≥ 80 % over 20-40
journal trades is ordinary luck on a 59 % process; (b) **unstated
selection** — the mechanical rule fires 11-13×/day; a human takes 2-5
using filters the stated setup doesn't contain (trend, session, news,
"clean" gaps) — if the 80 % is real it lives there, and is testable once
stated; (c) **open losers don't count yet** — with a stop ~3× the target,
winners resolve in minutes while losers hang for hours; counting mid-air
losers as not-losses inflates live win rate; (d) even a TRUE 80 % yields
+0.04R/trade before costs — a 75 % month is a losing month. Inverted R:R
has almost no room even when it works.

Fixes in the same commit: reject-branch trade rows recorded risk as
q×0.3×ATR regardless of geometry — now q×sdist (affects only the R
columns; win %/net/PF verified identical to the first run). Cost caveat
on record: exit legs charge the entry fee as maker even for reject-mode
taker entries (~0.001 % notional understatement — anti-conservative,
immaterial vs −100 % verdicts).

## v0.12-exp — FVG-wick 0.3:1 on gold 5m (2026-09-02)

User-supplied rule ("new strat I learnt"): gold, 5m, wait for a wick into a
fair value gap, trade 0.3:1. Mechanized spec: FVG on closed 5m candles
(≤20 candles old, unfilled), resting limit at the gap's proximal edge
(the wick fills it), direction with the gap, stop 0.3×ATR14 / target
1.0×ATR14 (breakeven ≈ 23.1 % + costs), maker in/target + taker stop,
futures-style costs, gap-guard on. Split 2006-2012 explore / 2013-2020
holdout; taint note: gold 2013-20 was used once for the unrelated EMA rule.
**Pre-registered pass:** explore n ≥ 100 ∧ net > 0 → holdout; holdout pass
requires net > 0 ∧ win ≥ 26 % ∧ maxDD < 40 %. Reported either way; no
geometry variations in response to results.

**Results (2026-09-02): FAIL — account destroyed in year one of BOTH eras.**
After two mechanization-fairness fixes (ATR-0 hygiene; one-trade-per-gap so
the sim doesn't machine-gun 46/day): explore 20.8 % win, PF 0.83, −100 %
within 2006; holdout 21.0 %, PF 0.53, −100 % within 2013. ~16-18 trades/day.

Two independent kill shots, either fatal alone:
1. **No entry edge:** win rate 20.8-21.0 % sits BELOW the 23.1 % zero-cost
   breakeven for the 0.3:1 payoff. Gap-taps continue vs reverse at rates
   that never reach the geometry's own bar, in either era.
2. **Geometry can't pay costs:** a 0.3×ATR stop on 5m gold is ~0.02 % of
   price; stop slippage alone (0.005 %) plus fees ≈ 0.3-0.5 R per losing
   round trip — avg realized loss −1.51 R on a 1 R stop. Expectancy
   ≈ −0.52 R/trade at 17/day. Structurally unpayable even at futures-grade
   costs — the VWAP-scalper disease in its most extreme form yet.

**v0.12b (user completed the spec): rejection-wick trigger — wick enters the
zone, BODY closes outside, enter next bar open.** Result: WORSE. Explore
18.7 % win / PF 0.72; holdout 15.3 % / PF 0.48; −100 % in year one, both
eras. Mechanism: the confirmation delays entry one bar past the bounce, so
the 0.3×ATR stop sits inside ordinary next-bar noise — the v0.5 lesson
(confirmation = lateness) at 5m scale, plus taker entry costs. Fourth
confirmed instance of the tight-stop law across both trigger readings.

Boundary note: verdict applies to the rule as stated (mechanical FVG-tap,
0.3:1). Any "it works when taught" residue would live in discretionary gap
selection — which is unfalsifiable and untradeable by a bot. Third
confirmed instance of the tight-stop law: stops far smaller than the
cost-per-trade floor cannot be rescued by any signal.

## v0.10c — Accidental candidate: 3×ATR symmetric bracket on extension entries (2026-09-01)

Discovered inside a teaching demo answering the user's "can we use 1:9?"
question: same 1-ATR EMA-distance entries as v0.10-exp, but exits via a
SYMMETRIC 3×ATR bracket instead of EMA-touch. On BTC 1H at full Bybit costs:
2023-24 +$8,393 (57.6 % win, longs carry) and 2025-26 +$5,340 (57.3 % win,
SHORTS carry) — win rate stable across the regime flip, profit rotating
sides. First candidate ever to show that signature.

**Taint acknowledged:** both windows are consumed data (v0.10-exp ran its
variant on them), so the above is in-sample evidence by our standards.

**Pre-registered validation (written before the run):** BTC 1H, 2019-01 →
2022-12 — an era never loaded by any EMA experiment (2021 mania, COVID
crash, 2022 bear). Same rule verbatim: |d| ≥ 1 entry next open, ±3×ATR
bracket, stop-first, 1 % risk, 10× cap, 0.055 % taker + 0.01 % slip.
PASS = net > 0 AND win % ≥ 52 AND both a bull and a bear year individually
net-positive. Anything less: reported, not adopted. No geometry variations
will be tried on the validation era regardless of outcome.

**VALIDATION RESULT (2026-09-01): PASS — the project's first validated
strategy.** BTC 1H, 2019-01 → 2022-12 (untouched era, 35,064 bars):
**1,508 trades, 58.0 % win, net +$36,925 (CAGR 47.3 %), Sharpe 1.68,
maxDD 15.6 %**, 64 % positive months (worst −7.6 %). Every calendar year
net-positive individually — including bear-2022 (+$5,006) — and both sides
contribute (longs +$21.7k / shorts +$15.3k). All three pre-registered
criteria pass.

Cross-era win-rate stability is the headline signature: 58.0 % (2019-22,
unseen) / 57.6 % (2023-24) / 57.3 % (2025-26) across ~3,100 trades at full
retail costs. Statistically: 58 % vs 50 % null over 1,508 trades ≈ 6σ;
survives any reasonable multiple-testing correction for this project's
~10 prior trials.

Interpretation: a 1H momentum-continuation effect — conditional on a 1-ATR
extension from the 200-EMA, continuation beats reversal ~58/42 at symmetric
3×ATR payoff, direction-agnostic. Consistent with the state-dependent
intraday-momentum literature (RESEARCH.md §2).

**Known boundaries / caveats, on record:** BTC-only so far (this exit was
never tested cross-market on clean data); crypto-era 2019-2026 only; perp
funding not modeled (execute on spot, or model funding before perp use);
demo-era results (2023-26) remain in-sample by our standards; live decay
unknown — the TRUE forward test is paper trading, which this result now
EARNS by the user's own bar (win rate + every-period profitability).

**Next steps:** wire as a bot strategy module (entries on 1H closes,
bracket orders) for forward paper trading; optional breadth check on
untainted markets/eras as data becomes available.

## v0.10b — EMA-distance rule, cross-market test (2026-09-01)

Follow-up to v0.10-exp ("is it the rule or the asset?"). Markets
pre-registered for economic diversity BEFORE any results: XAU (metal),
WTICO (energy), SPX500 (second index), 1H bars 2005-2020, futures-style
costs (0.002 % taker + 0.005 % slip). Split: explore 2005-2012 / holdout
2013-2020 (same eras as v0.11). Same grid and survivor rule as v0.10-exp.
Multiple-testing caveat ON RECORD: 18 exploration cells across 3 markets ⇒
~1-2 false survivors expected by chance; only holdout results count, and
any holdout pass at this trial count requires an additional era check
before adoption.

**Results (2026-09-01): asset-dependent — one genuinely interesting lead,
parked short of adoption.**

- **SPX500: dead.** No cell exploration-positive (trend PF 0.78-0.92) —
  matches NAS100/BTC: equity indices punish 1H extension-chasing.
- **XAU: weak pass, untradeable shape.** Trend cells exploration-positive
  (gold bull 2006-11), holdout net +$5.8k-10.3k but PF only 1.07-1.13 with
  **42-48 % drawdowns** — risk-adjusted garbage; not adoptable.
- **WTICO (oil): the outlier.** Trend cells positive in BOTH eras and ALL
  three thresholds — holdout PF 1.33/1.39/1.47, net +$45.8k-55.2k, maxDD
  33-36 %, profitable 6-7 of 8 holdout years (2014-15 collapse, 2018 Q4,
  2020 COVID all captured short). Grid-wide consistency, not one lucky cell.
- revert mode: −80-95 % in every market. Five markets, five catastrophes —
  the fade reading is conclusively dead.

**Why oil is NOT adopted (yet):** (1) pre-registered era-check requirement —
no third era exists in this archive (2005-2020 fully consumed); (2)
**commodity roll confound**: Oanda CFD price series don't expose
roll/financing; price-only PnL on oil misstates carry, materially for
multi-week holds — the single biggest validity risk; (3) 18-cell trial
count; (4) 33-36 % drawdowns at PF ~1.4 are survivable but harsh. Status:
**most promising unvalidated lead in the project** — requires post-2020
data + roll-aware cost model before belief. Parked on record.

## v0.11 — Diversified daily TSMOM portfolio (2026-09-01)

New strategy family, user-selected from the evidence-ranked menu: classic
time-series momentum (Moskowitz/Ooi/Pedersen construction) across every
instrument in the FutureSharks/Oanda archive (~17: equity indices, energy,
metals, grains, softs, bonds; daily bars resampled from 1m, 2005-2020).
Long trailing-L-day winners, short losers, equal-vol sizing (20d EWMA vol,
5 % floor, gross budget 2×, cap 3×), monthly resize + flip trades, 0.007 %
per side. This is the one family where the published evidence is FOR the
mechanized version — the edge is diversification across many small trends.

**Pre-registered protocol:** exploration 2005-2012, holdout 2013-2020-05.
Grid = lookback L ∈ {90, 180, 252} only. Survivor: exploration Sharpe ≥ 0.3
AND maxDD < 40 %. Survivors run the holdout ONCE. Holdout-positive with
Sharpe ≥ 0.3 = first validated strategy of the project; anything less is
reported as-is. No parameter additions in response to results.

**Results (2026-09-01): NOT VALIDATED — and the failure replicates the
literature's own timeline.**

All 17 instruments built (no skips), panel 2005-01 → 2020-05, 4,786 days.
- EXPLORE 2005-12: **L=90 Sharpe 0.43, CAGR 4.7 %, maxDD 17 %** — survivor
  (notably +9.3 % through 2008, the classic crisis-alpha signature).
  L=180 Sharpe 0.19, L=252 Sharpe −0.07 — no.
- HOLDOUT 2013-20: **L=90 Sharpe −0.21, CAGR −2.5 %, maxDD 31 %.** FAIL by
  the pre-registered bar (holdout Sharpe ≥ 0.3).

Context that matters: our holdout window IS the documented "CTA winter" —
published trend indices (BTOP50, SocGen CTA) were flat-to-negative through
2013-2019 as QE-era markets chopped, after a golden 2005-2012. Our
replication found exactly that: the strategy's edge lived where the
literature says it lived and died where the literature says it weakened.
Honest limits of our test: 17 CFD instruments (institutional CTAs run
50-100+ incl. FX/rates), one sizing scheme, data ends 2020-05 — the 2020-22
revival documented for CTAs is outside our archive.

**Disposition per pre-registration: not adopted.** No parameter fishing in
response. Natural extension IF ever pursued: post-2020 multi-asset data and
wider breadth — logged as a possibility, not a plan.

## v0.10-exp — 1H 200-EMA distance experiment (2026-08-18)

User-proposed, separate from the ICT family: 200-EMA on 1H, act when price
is "fairly" away from it. The proposal's wording was direction-ambiguous
(titled trend-following, described as fading), so BOTH mirror rules run:
`trend` (d ≥ +T → LONG) and `revert` (d ≥ +T → SHORT), d = (close−EMA200)/
ATR14, exits on EMA touch + 2×ATR stop, entries next-bar-open at taker cost.
Literature prior (RESEARCH.md): higher-TF trend rules are among the few
cost-survivors in crypto — this is the first tested idea whose target size
(0.5-2 %) dwarfs its cost (0.01-0.1 %).

**Pre-registered protocol (written before results):** exploration grid
T ∈ {1,2,3} × {trend, revert} on BTC 2023-2024 (Bybit costs 0.055 %+0.01 %)
and NAS100 2015-2017 (futures costs 0.002 %+0.005 %). A cell survives
exploration only with n ≥ 20 and net > 0; survivors run ONCE on the
untouched holdouts (BTC 2025→2026-07, NAS100 2018→2020-05). Only
holdout-positive cells earn further attention. The grid is labeled
exploration — its in-sample winners carry no evidential weight on their own.

**Results (2026-09-01): NO CELL VALIDATED — and the protocol earned its keep
twice over.**

BTC exploration (2023-24) made all three TREND cells look excellent
(net +$18.4k/+$10.2k/+$8.2k, PF 1.31-1.44) while every REVERT cell — the
message's literal "fairly above → short" reading — was ruinous (PF 0.72,
−73-79 % drawdown). But on the untouched holdout (2025→2026-08) **all three
trend survivors went negative** (−$2.3k/−$1.6k/−$2.4k, PF 0.83-0.90): the
exploration edge was the 2023-24 bull regime, not a durable rule. NAS100:
no cell was even exploration-positive (PF 0.82-0.96, sign-flipping years);
nothing advanced.

Findings: (1) the fade reading is catastrophically wrong on crypto — testing
both directions was not pedantry; (2) an "obvious" recent-window backtest
(2023-24 only) would have shipped a PF-1.44 illusion — the identical failure
mode as the ICT 2026-window results, caught this time in a single pass by
design; (3) the trend cells show the classic profile (19-21 % win, big
winners) but don't clear costs+chop across regimes at 1H on a single asset —
consistent with the literature, where surviving trend edges live on daily
bars across diversified assets with vol targeting. Disposition: rule NOT
adopted; harness (`backtest/ema_experiment.py`) retained as the template for
future quick strategy screens.



## v0.9 — HOME-INSTRUMENT TEST: NAS100 (Nasdaq-100) 2015→2020 (2026-08-17)

ICT's concepts are taught on index futures, not crypto perps. After the v0.8
BTCUSDT shelving, this tests the SAME two configs — v0.3 RB and v0.3+FVG,
zero parameter changes, committed defaults — on the strategy's home
instrument.

**Data**: Oanda NAS100 (Nasdaq-100 CFD) 1m, 2015-01 → 2020-05 (5.4 years,
1.83M candles; source FutureSharks/financial-data, UTC timestamps verified
empirically via the DST drift of the 9:30 ET volume spike, converted to NY).
Caveats, stated up front: index CFD prices as a proxy for NQ futures (same
price action, no exchange volume — irrelevant, the ICT pipeline is
price-only); data ends 2020 (fully out-of-sample vs both ICT's 2022 lessons
and all our development); ~89 % minute coverage (thin overnight minutes
absent from tick-derived bars).

**Economics (futures-style)**: maker 0.001 % / taker 0.002 % / slippage
0.005 % — models NQ e-mini's ~$2.5-3 per-side all-in cost on $85-260k
notional. Fee scenarios re-sweepable analytically from trade lists afterward.

**Pre-registered criteria, per config**: (1) n ≥ 100; (2) overall
gross/trade > 0; (3) gross-positive in ≥ 4 of 6 calendar-year buckets (2020
is a partial year, noted); (4) no year worse than −15 % net at the above
costs. PASS → the concept family has measurable edge on its home instrument;
next step is out-of-sample extension (2005-2014 held in reserve, unseen).
FAIL → the family is concluded — no instrument left where it's claimed to
work best. No parameter changes permitted in response to results.

**First RB pass (2026-08-17): INVALIDATED by a simulator artifact — and the
artifact is the whole result.** Raw output: 44 trades, +48.7 %, PF 2.38. But
the top trade (+$5,845, 2020-03-16 limit-down day) was a gap-fill bug: the
resting long limit filled 465 pts below the intended entry at the COVID gap
open, kept the signal's ORIGINAL stop — now 465 pts ABOVE the fill — and
booked the bounce to that "stop" as a +1R win. Live, a stop resting above
market triggers instantly; the trade would have been a scratch. Adjusted
result: **−$972 over 5.4y, mean −0.12 R/trade** (31.8 % win, +1.91R winners
vs −1.06R losers), n=44 (< the 100 floor), 2017 produced zero trades.

**Engine fix (v0.9.1)**: `_gap_invalidates()` — a fill at/beyond the signal's
stop cancels the order (counted under orders_expired) instead of opening a
position with a wrong-side stop. Applies to both ICT and VWAP pending limits.
Lesson: every windfall trade in a backtest must be audited before belief —
one artifact manufactured a +48.7 % illusion on an otherwise negative system.

**Final verdict (2026-09-01): BOTH CONFIGS FAIL — the ICT mechanization
family is concluded on its home instrument too.**

Method note: repeated container recycles kept killing the 4-hour clean
reruns, so the clean RB result was computed ANALYTICALLY — the v0.9.1 gap
guard applied to the preserved dirty-run trade list (the guard's effect is
exactly the removal of wrong-side-stop trades, identifiable by their
impossible profitable-"SL" signature). Exactly one such trade existed
(2020-03-16, +$5,845).

**Clean RB (NAS100, 2015→2020-05): n=43, 30.2 % win, gross −$876, net −$971,
PF 0.72, −0.14 R/trade.** Per year: 2015 +$359, 2016 −$141, **2017 zero
trades**, 2018 −$193, 2019 −$597, 2020 −$398. Criteria: n ≥ 100 FAIL (43);
gross/trade > 0 FAIL (−$20); ≥ 4/6 years gross-positive FAIL (1/6); year
floor pass. **FVG:** interrupted at 86 % with 7 trades / −$383 — the n ≥ 100
floor is arithmetically unreachable; FAIL regardless of completion.

**The full arc, closed:** the mechanized Powell/ICT strategy family is
gross-negative across regimes on BTCUSDT (v0.8) AND on the Nasdaq-100 it was
designed for (v0.9), under honest fills and costs, with every variant,
filter, and entry style the source material prescribes having been tested
one change at a time. What survives: the audited bot codebase, a
deterministic multi-market backtest engine with gap-guarded fills, the
explore/holdout screening harness, 10 versions of documented negative
results with named mechanisms, and the discipline that produced them.

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

## v0.8 — REGIME TEST: 2023→2026 multi-year validation (2026-07-22)

User standard: the 180d results aren't strong enough to justify paper
trading. Correct response is more DATA on the surviving configs, not more
tuning. Both survivors (v0.3 RB, v0.3+FVG) run unchanged over 3.55 years of
1m data (2023-01 → 2026-07: the 2023 recovery, 2024 bull, 2025 top, 2026
bear; 1.87M candles, zero gaps; cache too large to commit — regenerate via
DEVLOG instructions / `--cache-file`).

**Pre-registered criteria, per config:** (1) win rate within ±10 pp of its
180d value; (2) gross per trade positive over the full period AND in at
least 3 of 4 calendar years; (3) no year worse than −15 % net at Bybit
retail fees; (4) combined sample ≥ 60 trades. PASS → the config earns
paper-trade/forward validation. FAIL → strategy shelved for this instrument.
No parameter changes are permitted in response to these results.

**Backtest (2026-07-22): BOTH CONFIGS FAIL — strategy shelved per
pre-registration.**

| Config | Trades | Win % (180d ref) | Gross total | Gross/trade | Net @ retail | Max DD |
|---|---|---|---|---|---|---|
| v0.3 RB | 118 | 34.7 (45.5) | **−$578** | −$4.9 | **−49.6 %** | 51 % |
| v0.3+FVG | 53 | 28.3 (50.0) | **−$1,264** | −$23.9 | −31.9 % | 34 % |

Per-year gross/trade (v0.3): 2023 +$1, 2024 +$2, **2025 −$38**, 2026 +$12.
Per-year (FVG): 2023 −$31, 2024 −$26, **2025 −$40**, 2026 +$20.

Criteria: win-rate band — v0.3 34.7 % vs ≥35.5 % FAIL; FVG 28.3 % vs ≥40 %
FAIL. Gross/trade positive overall — both FAIL. Year floor (−15 %) — v0.3
breaches in 2024 and 2025; FVG borderline in 2024. Only the sample-size
criterion passed.

**The decisive finding: both configs are gross-NEGATIVE over 3.55 years —
no fee tier can save a strategy with no gross edge.** The 2026 window we
measured everything on (48-50 % win, positive gross/trade in BOTH configs)
was the friendliest regime in the whole dataset; the 180-day results were
substantially regime luck, exactly the in-sample selection effect the
overfitting literature (RESEARCH.md §3) describes. 2025 was catastrophic
for both variants.

**Disposition per the pre-registered rule: the mechanized strategy family is
SHELVED for BTCUSDT.** No parameter changes in response to these results; no
paper trading. R8 and all queued candidates are moot for this instrument.
What remains valid: the audit fixes, the backtest engine, the fee analysis
method, and the documented negative — which prevented months of forward
testing (or live losses) on a regime-lucky system.

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
