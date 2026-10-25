# P2 primitive probes: pre-registration (phase 2 of the strategy catalogue)

Status: written by the statistician, amended and frozen by the chair on 2026-10-11, committed and pushed
before any probe runs. The grid (section 7) may change only by an amendment appended to section 16 BEFORE
the first probe runs; after that, never. Arithmetic, tiers and the full probe table:
`research/prereg/P2_power_table.md`. The scripts behind its numbers are in `research/prereg/scripts/`
(re-run by the chair: tier counts 102 / 27 / 21 / 51 and the 0.942 sub-half correlation reproduce).
Family: `catalogue-P2`. Phase 2 of `docs/CATALOGUE.md`.

## 1. Purpose

Measure, with no wrapper, the information content of every published primitive that can be computed
from data we hold (tier T1), on the EXPLORE quadrant only, and report when each holds (by pre-stated
regime). The output is a primitive map and a ranked list of candidates for phase 3. **Nothing in phase 2
can pass.** No explore result is evidence of an edge; it can only earn a phase-3 combination a place in
the single sealed batch (section 11).

## 2. Split (fixed; `backtest/edge_lab/split.py`, `research/prereg/split_assignment.csv`)

- Coins: 715 symbols ranked by lifetime median daily quote volume, paired 1-2, 3-4, ..., and in each
  pair the smaller sha256("edge-split-v036" + symbol) goes to half A. 358 in A, 357 in B.
  **BTCUSDT is in half B.**
- Era: explore = bars stamped on or before 2024-12-31 (EXPLORE_END); sealed era = 2025-01-01 to the data
  end (2026-09-30).
- EXPLORE quadrant = (early era, half A): 191 coins, 135,228 coin-days (23.3 %), 1,827 calendar days.
- Sealed: late_A 153,618 coin-days; early_B 137,774; late_B 153,060 (76.7 %). New calendar dates in the
  sealed set: 638 (2025-01-01 to 2026-09-30). early_B shares explore's dates.
- The split is not changed by this document.

## 3. Data and preconditions (all before the first probe)

T1 data only: `backtest/data_cache/local/edge/klines_1d_um/<SYMBOL>.csv` (timestamp = UTC open; open,
high, low, close, volume, quote_volume, trades) and `funding/<SYMBOL>.csv` (timestamp, rate, interval_h,
f8), for half-A symbols, bars and settlements stamped on or before 2024-12-31.

Preconditions, each signed off by the data engineer, all outcome-blind:

1. **Patch the 1d gaps**: 2022-02-26..28 is missing for 21 of the 67 half-A coins spanning that date;
   186 missing calendar days in all inside half-A explore spans. Patch from the daily archive files;
   re-load through the consumer loader; report remaining gaps. No forward filling.
2. **Funding for every half-A coin that ever enters U50A** (54 of 191 half-A symbols have no file
   today). Half A only.
3. **Loader guard**: every read goes through a loader that asserts `split.is_explore(symbol, ts)` for
   every row it returns and refuses BTCUSDT, any half-B symbol, any bar stamped 2025-01-01 or later, and
   `universe_pit.csv` (its ranks mix both halves). A planted half-B row and a planted 2025 row must make
   the self-test raise.
4. **Outcome-blind funnel** per cell: windows, trades, names per day, per year. Cells below their
   feasibility floor (section 6, G8) are listed and not run.

## 4. Universe, market proxy, timing, costs

- **U50A**: each UTC day t, the 50 half-A coins with the highest median daily quote volume over the 30
  days ending t-1, among coins with volume > 0 on t-1 and at least 90 live days (live = volume > 0).
  A cell needing a lookback of L days also needs L live days. Cross-sectional cells need at least 10
  names (first such day 2020-05-09).
- **MKT_A10**: the 10 top U50A coins by the same rank; daily return = equal-weight mean of their
  close-to-close log returns; window return = equal-weight mean of their `trade_return(open, h)`. At
  least 5 names (from 2020-04-18). Used as the hedge (`mkt_ret`), the factor in residual models and the
  basis of every regime. The same half-A MKT_A10 is used in every quadrant.
- **Timing**: decide at the close of the 1d bar stamped t (00:00 UTC of t+1); enter at the open of t+1;
  exit at the open of t+1+h (`measure.trade_return`). Monthly cells decide at the close of the last UTC
  day of the month; weekly cells at the close of Sunday UTC unless the card fixes the weekday.
- **Costs**: 13 bp round trip per leg (`measure.ROUND_TRIP_BPS`). Net is reported at 1x, 1.5x and 2x cost
  (U50A reaches overall liquidity rank about 100, where 13 bp is optimistic).
- **Funding paid**: for a position held over (entry, exit], the sum of `rate` x 1e4 over that coin's
  settlements stamped in (entry, exit], positive = longs pay (Binance convention, H001 report section 3).
  Never `f8` (19 % of half-A explore settlements are on 4 h or 1 h intervals). Passed to
  `information_test(funding_bps=...)` as paid by a long; long-short legs: the long leg pays its rate, the
  short leg receives its rate.
- **Dead coins**: zero-volume (zombie) rows are not live. A trade whose exit falls after the coin's last
  live bar exits at the last live close and is counted and flagged. A zero-volume stretch of more than 3
  days inside a coin's life restarts its history counter. Each ticker is its own instrument (MATIC/POL,
  RNDR/RENDER, AGIX and OCEAN/FET, ...).

## 5. Tiers (probe level, `P2_power_table.md` section 2)

| tier | probes | in this run |
|---|---|---|
| T1 (1d klines and/or funding held) | 102 | yes: 73 gridded, 13 collapsed onto other cards' cells, 5 unspecified, 8 deferred composites, 3 infeasible |
| T2 (needs a download, calendar or external series) | 27 | no; each needs a data report and an amendment to this file before it runs |
| T3 (15 m or finer, tick) | 21 | no |
| P (parked) | 51 | no |

## 6. Grid rules

- **G1** Published values only; no extension; no interpolation. A card publishing only a range adds no
  values; it collapses onto values other cards published inside the range.
- **G2** Holds: the card's fixed hold; if signal-defined or absent, H1 = {1, 7, 30} days for 1d bars,
  {1, 4} weeks for 1w bars, {1} month for 1mo bars. Signal-defined exits are stripped.
- **G3** One cell per (archetype, variable, parameters, hold, universe type). With-state and
  against-state cards on one key are one signed cell; each card's predicted sign is recorded with it.
  Every TS/LEVEL state is oriented so that +1 = the "up" state (high in range, above, overbought,
  bullish pattern) and -1 the mirror; reversal cards predict a negative effect.
- **G4** Wrappers stripped (gates such as close > SMA200, stops, targets, confirmation bars, exits).
- **G5** Named-pattern families pooled per card (bullish set vs bearish set).
- **G6** Composite models deferred to phase 3.
- **G7** A missing non-hold parameter means no cell (S-MR-07b, S-XS-10b, S-PAT-06a, S-PAT-06b, S-XS-12c).
- **G8** A cell with fewer than 12 independent explore windows is not run (S-CAL-05a, S-CAL-04a,
  S-XS-10a, the 36-month hold of S-TREND-01a); F-A runs only if its funnel reaches 12.
- Computed per cell: the pooled statistic and the regime breakdown of section 8. Nothing else (no
  long/short leg split, no per-coin view, no per-pattern view).

## 7. The grid: 304 cells

H1 = {1, 7, 30} d. "q" = quantile per leg passed to `cross_sectional_ls`. Definitions are at the close of
t from data stamped on or before t. Full source mapping: `P2_power_table.md` section 3.3.

### TS_STATE (163 cells; pooled single-asset panel over U50A unless "on MKT_A10")

| family | definition | parameters | holds | cells |
|---|---|---|---|---|
| TS-A | sign of the L-month log return, month-end decisions | L = 1, 3, 12 | 30 d | 3 |
| TS-B | sign of the 365-day log return, daily | | 1, 7 d | 2 |
| TS-C | +1 if the week's return >= the 80th, -1 if <= the 20th percentile of the coin's first 104 weekly returns (coin excluded until it has 104 weeks) | | 1, 2, 3, 4 weeks | 4 |
| TS-D | on MKT_A10, month-end: 4 states of (sign 12-month, sign 1-month); 3 contrasts vs the all-month mean | | 1 month | 3 |
| TS-E | on MKT_A10: sign of -(4r_t + 3r_t-1 + 2r_t-2 + r_t-3), daily log returns | | 1 d | 1 |
| TS-F | +1 if close_t is the highest close of the last L bars (t included), -1 if the lowest | L = 5, 7, 10, 20, 30, 55, 60, 90, 150, 250, 360 | H1 | 33 |
| TS-G | +1 if SMA_f > SMA_s x (1+b), -1 if SMA_f < SMA_s x (1-b) | (f,s) = (1,50), (1,150), (5,150), (1,200), (2,200); b = 0, 0.01 | 1 d | 10 |
| TS-H | the day the TS-G state changes sign (crossover event) | as TS-G | 10 d | 10 |
| TS-I | sign(SMA50 - SMA200) | | H1 | 3 |
| TS-J | month-end close above (+1) / below (-1) the mean of the last 10 month-end closes | | 1 month | 1 |
| TS-K | sign(EMA12 - EMA26); MACD(12,26) crossing its EMA9 (sign of the cross); Tenkan(9) crossing Kijun(26); sign(+DI14 - -DI14), Wilder; sign(HMA20_t - HMA20_t-1); sign(HA close - HA open) | as listed | H1 | 18 |
| TS-L | close above / below SMA10(typical price) +- SMA10(H-L); close above / below (H+L)/2 +- 3 x ATR10 (Wilder; values recalled on the card, flagged) | | H1 | 6 |
| TS-M | (+1 / -1) %b(20, 2, population sd) > 1 / < 0; CCI(20, 0.015) > 100 / < -100; CCI crossing back inside +200 from above / inside -200 from below; RSI2 (Wilder) > 95 / < 5; RSI2 > 95 / < 10; RSI14 crossing back below 70 / above 30; Williams %R(14) > -20 / < -80 | as listed | H1 | 21 |
| TS-N | z = (close - SMA_L) / sd_L with L = round(half-life) from an expanding OLS of dy on y (log price, at least 90 d; no signal if lambda >= 0), sign; IBS = (C-L)/(H-L) > 0.8 / < 0.2; close beyond open +- 2 x SMA10 of min(H-O, O-L) through t-1 | | 1 d; 1 d; 10 d | 3 |
| TS-O | pairs inside U50A, re-formed at each month start from the 365 days ending then, valid for 6 months, open when the spread is beyond 2 formation sd, lag 1 day, long the cheap leg and short the rich leg at equal notional: distance (min SSD of normalised prices), top 5 and top 20 pairs; Engle-Granger residual of the closest-SSD pairs passing at 1, 5, 10 %, top 5, 10, 20, 40 pairs; Kalman hedge ratio (delta 1e-4, R 1e-3, band 1 forecast sd) on the top-5 distance pairs | as listed | H1 | 45 |

Orientation note for TS-M: every oscillator cell is oriented "+1 = up/overbought" (RSI2 > 95 is +1, RSI2
< 5 is -1). The reversal cards (S-MR-01a, 02a, 02c, 03a, 05b) therefore predict a negative effect and the
breakout cards (S-BRK-08c, S-MR-05a) a positive one; each cell carries both predictions.

### XS_RANK (76 cells; `cross_sectional_ls` within U50A, equal weight, rows spaced at the hold)

| family | signal | parameters | q | holds | cells |
|---|---|---|---|---|---|
| XS-A | J-month return, skip 0 or 1 week; overlapping monthly cohorts (month return = mean of the K live cohorts; each cohort charged one full-turnover cost) | J, K = 3, 6, 9, 12 | 0.1 | K months | 32 |
| XS-B | L-week log return | L = 1, 2, 3, 4, 12, 26 | 0.2 | 1 week | 6 |
| XS-C | Wednesday-to-Monday return ranked at Tuesday's close (skip Tuesday) | | 0.2 | 1 week | 1 |
| XS-D | 2-week return | | 0.2 | 2 weeks | 1 |
| XS-E | 14-day return, top 30 % minus bottom 30 %, inside the most liquid and the least liquid 30 % by 14-day Amihud | 2 contrasts | 0.3 | 14 d | 2 |
| XS-F | 1-day return | | 0.2 | 1 d | 1 |
| XS-G | 1-month return | | 0.2 | 1 month | 1 |
| XS-H | return of month t-12 | | 0.1 | 1 month | 1 |
| XS-I | minus the 52-week return | | 0.3 | 1 week | 1 |
| XS-J | close / prior 52-week high, 1-month skip (recalled values, flagged) | | 0.3 | 6-month overlapping cohorts | 1 |
| XS-K | ln close - ln max(high) over h weeks | h = 1, 2, 4, 12, 26 | 0.2 | 1 week | 5 |
| XS-L | mean of the N largest daily returns of the prior month | N = 1..5 | 0.1 | 1 month | 5 |
| XS-M | sd of daily residuals vs MKT_A10, formation/gap/hold | 1/0/1, 1/1/1, 12/1/12 months | 0.2 | as listed | 3 |
| XS-N | beta vs MKT_A10: 0.6 x (corr of 3-day log returns over 5 y, at least 750 d) x (sd ratio over 1 y, at least 120 d) + 0.4; long low, short high; beta of the spread reported (no leverage to beta 1) | | 0.5 | 1 month | 1 |
| XS-O | residual momentum: sum of residuals t-12..t-2 of a 36-month regression on MKT_A10, divided by their sd | | 0.1 | 1, 3, 6, 12 months (cohorts) | 4 |
| XS-P | PCA s-score: 15 PCs of the 252-day correlation of U50A returns, 60-day residual OU fit (kappa > 252/30); +1 at s > 1.25, -1 at s < -1.25; outcome = factor-hedged residual return, cost 2 legs | | event | H1 | 3 |
| XS-Q | IBS; long the lowest, short the highest single name | | k = 1 | 1 d | 1 |
| XS-R | last settled f8 with stamp before the decision instant; long lowest, short highest; funding of both legs added (`rate`) | | 0.2 | H1 | 3 |
| XS-S | day-50 dollar volume ranked inside the coin's own 50 days, non-overlapping 50-day formation grid from 2020-05-09; long rank >= 46, short rank <= 5 (at least 3 names a leg) | | groups | 1, 10, 20 d | 3 |
| XS-T | last week's dollar volume ranked inside the coin's own 10 weeks; long 10, short 1; decisions on a 20-day grid | | groups | 20 d | 1 |

### VOL_STATE (41 cells)

Outcome for V-A to V-G: y = ln(mean |daily return| over t+1..t+h / mean |daily return| over t-89..t)
on state coin-days, minus the mean of y over all eligible U50A coin-days; pooled; `cluster_mean_t`.
V-G is the contrast on sell days vs buy days. V-H is the alpha of the vol-scaled MKT_A10 on the unscaled
MKT_A10 (the `information_test` hedged-alpha arithmetic with mkt_ret = unscaled), month clusters.

| family | state | holds | cells |
|---|---|---|---|
| V-A | ADX(14, Wilder) < 20; > 40 | H1 | 6 |
| V-B | BB(20,2) bandwidth within 3 % of its 125-day low | H1 | 3 |
| V-C | TTM squeeze fires (first bar with BB(20,2) back outside Keltner(20, 1.5 ATR)) | H1 | 3 |
| V-D | inside bar; ID/NR4 | H1 | 6 |
| V-E | NR4; NR7 | H1 | 6 |
| V-F | NR4; NR7 | 10 d | 2 |
| V-G | the 10 TS-G rules: next-day abs return, sell vs buy days | 1 d | 10 |
| V-H | exposure c / sigma-hat: EWMA half-life 10, 20, 90 d (data to t-2), daily; EWMA com 60, monthly; c / prior-month realised variance, monthly | 1 d; 1 month | 5 |

### LEVEL_TOUCH (21), CLOCK (2), FLOW_STATE (1)

| family | definition | holds | cells |
|---|---|---|---|
| L-A | any of three white soldiers, three inside up, three outside up, morning star (+1) or their mirrors (-1), with the 3-day-MA trend rule over t-6..t (at most one violation), body conditions dropped | 1, 2, 3 d | 3 |
| L-B | the 28 signals of S-PAT-01b pooled into single-line and reversal families, 10-day EMA trend rule, decided at the close of the day after the signal. The 28 definitions must be taken from the source before the build; if they cannot be, L-B is "unspecified" (G7) | 10 d | 2 |
| L-C | the 10 kernel-regression patterns (window 38 = 35 + 3, bandwidth 0.3 x CV, detection lag 3), pooled bullish vs bearish | 1 d | 1 |
| L-D | head-and-shoulders (-1) / inverse (+1) with a neckline break before E6, entry 3 days after E6 | 20, 40, 60 d | 3 |
| L-E | setup at t-1 = NR4, NR7, ID/NR4 or inside bar; close_t above its high (+1) / below its low (-1) | H1 | 12 |
| C-A | MKT_A10: days -1, 1, 2, 3 around the UTC month boundary vs other days | 4-day window | 1 |
| C-B | MKT_A10: Saturday and Sunday UTC vs weekdays | 1 d | 1 |
| F-A | per coin: 30-day mean f8 < 0, long | 90 d | 1 |

**Total: TS 163, XS 76, VOL 41, LEVEL 21, CLOCK 2, FLOW 1 = 304 cells.** With the regime breakdown,
5,092 views.

## 8. Regimes (reported for every cell; definitions in `P2_power_table.md` section 6)

R1 trend: sign of the 90-day MKT_A10 log return (up/down). R2 volatility: 30-day MKT_A10 vol as a
percentile of its trailing 365 days (terciles). R3 funding: cross-coin median of each U50A coin's 7-day
mean f8 (< 0.5, 0.5-1.5, > 1.5 bp per 8 h). R4 liquidity: 30-day mean quote volume of the MKT_A10
constituents, percentile of trailing 365 days (terciles). R5 calendar year. R6 (XS families only):
cross-sectional sd of 7-day returns, percentile of trailing 365 days (terciles). All known at the close
of t; all built from half-A data; no sealed-era regime frequency may be computed before the open.

## 9. Outcome metrics

- **TS_STATE, LEVEL_TOUCH, FLOW_STATE**: per coin, `measure.information_test(signal, trade_return(open,
  h), h=h, cost_bps=13, funding_bps=<section 4>, mkt_ret=<MKT_A10 window return>)`. Pooled: concatenate
  the per-coin de-overlapped trade series (drift-matched excess, net, hedged alpha) built exactly as
  `information_test` builds them, and apply `measure.cluster_mean_t`. Self-test: with one coin the
  pooled t equals that coin's `t_excess`. Clusters: W for h = 1, M for 2-14 d, Q beyond (cross-coin
  windows overlap, so the cluster must be at least the hold).
- **Market-wide series** (TS-D, TS-E, C-A, C-B, V-H): the series' own `information_test` or de-meaned
  bucket mean via `cluster_mean_t` (W; M for monthly series).
- **XS_RANK, pairs, PCA**: `measure.cross_sectional_ls` (or the leg arithmetic it uses, for group sorts),
  gross and net series, `cluster_mean_t` (W up to 7-day holds, M for 14-30 days and cohort composites);
  spread regressed on MKT_A10 for beta and alpha.
- **CLOCK/EVENT**: date-clustered de-meaned bucket means on MKT_A10.
- **CARRY** (T2 cash-and-carry, not in this run): realised funding minus the adverse basis move, four
  legs of cost, month clusters.
- **VOL_STATE**: section 7.

## 10. What is reported per cell

n trades, n windows and clusters, names per day; gross raw, gross drift-matched excess with its clustered
SE and t; cost ratio; net at 1x, 1.5x, 2x cost; hedged alpha and t; beta; hit rate; sd per trade (raw and
0.5/99.5 % winsorised); share long; per-year gross excess and n; the regime breakdown; the top-5 coins'
share of the total excess; the funnel; the card(s) and their predicted sign; the descriptive-only flag
(`P2_power_table.md` section 3.3: 129 cells). Every cell is reported, including empty and failed ones.

## 11. Not allowed

- Reading any (coin, date) outside the explore quadrant, BTCUSDT included, or computing anything on the
  sealed quadrants (returns, state counts, regime frequencies) before the batch open.
- Extending or interpolating a published grid; adding horizons; choosing cost level, cluster, universe or
  quantile after a result is seen.
- Dropping, re-running or redefining a cell after its result is seen. A bug fix re-runs the WHOLE family,
  and both versions are reported and logged.
- Computing views not listed in section 10 (legs, per coin, per pattern).
- Calling any phase-2 or phase-3 result a pass, or using it as evidence for itself.
- Opening the sealed set except as one batch under section 13.

## 12. Nomination rule (phase 3 to phase 4)

A combination (at most two primitives and at most one regime conditioner, from phase-2 cells) may be
nominated only if ALL of these hold on EXPLORE (detail in `P2_power_table.md` section 5.3): mechanism,
predicted sign, horizon and regime committed before its explore read; market-neutral form (unless the
late-only directional read is resolvable); gross excess >= 3 x the form's round trip (39 bp single leg,
78 bp two legs or a full-turnover long-short) and net > 0 at 1.5 x cost; explore clustered t >= 3.0,
hedged t >= 2 where directional, panel null-shift p < 0.05; predicted sign in at least 4 of 5 qualifying
explore years (minimum 3); plateau share_similar >= 0.5 over published neighbours; `power.n_required(0.5 x
effect, window sd, t_bar=2.576, power=0.5)` <= the sealed windows of its form; truncation guard empty on
every signal, universe and regime series and auditor stage A signed off; correlation with every other
nominee < 0.5; at least 80 % of trades in coins with a Bybit perp listed at the time.

Kill rule: a combination that fails any of these on explore is logged and never opened. A family with no
cell reaching |gross| >= 13 bp at |t| >= 2 in market-neutral form is recorded as "absent at cost" in the
primitive map.

## 13. Sealed-open rules (phase 4)

- **One batch of at most 5 nominees**, all pre-registered in one file, committed and pushed, registered
  with `ledger.register(n_cells = batch size, primaries = batch size)`, engine audited, then opened
  together. No second batch on these sealed data; unused opens are forfeited.
- **t-bar 2.576 = `ledger.bonferroni_t(5)`**, fixed now whatever the batch size. Deflated Sharpe > 0.95
  with n_trials = 5. DSR with the global count reported, not a bar.
- **Pass bars, all required**: sealed windows >= the n_required fixed at nomination; date-clustered t >=
  2.576 in the predicted direction (market-neutral: pooled over late_A, early_B, late_B; directional:
  late_A plus late_B only); gross cost ratio >= 3; net > 0 at 1x and 1.5x cost with real funding; hedged
  alpha > 0, t >= 2; late era alone with the predicted sign and net > 0; early_B alone with the predicted
  sign; at least 60 % of years with 10 or more trades positive; panel null-shift p < 0.05.
- **Reported, not selected on**: each quadrant, each regime level, each cost level. No quadrant, coin,
  year or regime dropped; no rerun.
- **Hurdle**: directional forms against the 14-15 %/yr pre-tax VGS/VAS hurdle; market-neutral forms by
  Sharpe, return on gross capital and monthly correlation to MKT_A10 and to VGS/VAS. State which.
- **A pass goes to auditor stage B**, then the forward paper tracker. "Nearly passed" is a fail.
- Known leaks recorded with each nominee: early_B shares explore's dates; late_A shares its coins; the
  2025-26 market path is public knowledge; H001, H010 and the v0.10-v0.35 ledger already read parts of
  the sealed era (funding-tail and OI-tail counts; 5m-1h data for ETH, XRP, BNB, ADA, DOGE, BTC, SOL,
  LINK); the split's pairing used lifetime volume.

## 14. Auditor checklist before the first probe

1. **Lookahead at close time.** Every input stamped on or before t; universe from volume through t-1;
   rolling statistics, percentiles, quantile cutoffs, pair formation, PCA, betas and residual models end
   at t; funding settlements with a stamp before the decision instant only; monthly and weekly series
   built from daily bars by CLOSE time. `truncation_guard` empty at (0.5, 0.7, 0.9) on every signal,
   universe and regime series; planted-signal self-tests reproduce exactly.
2. **Survivorship through zombie rows and delisted coins.** Zero-volume frozen bars excluded; constant
   1 bp zombie funding excluded; delisted coins present while alive (FTTUSDT is in half A); exits after
   the last live bar handled per section 4 and counted; suspension gaps restart the history counter.
3. **Listing-date bias.** 90 live days before entry to U50A; L live days for an L-day lookback; first
   cross-sectional date 2020-05-09; names per day reported; no history backfilled; each migrated ticker
   separate.
4. **Funding-sign and unit trap.** Positive rate = longs pay; `funding_bps` is what a LONG pays per
   window; paid funding sums `rate`, never `f8`; f8 only for levels (R3, XS-R ranking); interval
   switches inside a window handled; coins without a funding file fetched, never zero-filled.
5. **Overlapping holds de-overlapped.** Per coin by `non_overlapping_mask` (the `information_test`
   default); across coins by clusters at least as long as the hold; XS rows spaced at the hold; cohort
   composites at month level; fewer than 30 clusters flagged.
6. **Quadrant enforcement.** The loader guard of section 3 is tested; no BTC anywhere; no
   `universe_pit.csv`.
7. **Data gaps.** The 2022-02-26..28 patch verified; returns spanning a missing day are NaN.
8. **Fat tails.** Kurtosis of daily returns is about 190 in explore (LUNA- and FTT-type days). Report a
   winsorised sensitivity; never drop a day.
9. **Bracket and sign sanity** for any pair or spread leg: long leg return minus short leg return,
   checked on a planted pair.

## 15. Ledger (decided by the chair)

Phase 2 is exploration: it has no primary and does not use `register()`. The chair adopted the
statistician's proposal. `backtest/edge_lab/ledger.py` now has `log_catalogue_explore(phase, n_cells,
n_views, grid, grid_sha256, note)`, `catalogue_trials()` and `trials_for(lineage)`, plus a `lineage`
field on `register()`; self-test `t_catalogue_ledger` shows that catalogue cells do NOT enter
`total_trials()` (still 71) and DO enter `trials_for("catalogue")`. Phase 2 is logged ONCE, before the
first probe runs, as `log_catalogue_explore(2, 304, 5092, "research/prereg/P2_primitive_probes.md",
sha256 of this file at that moment, note)`. Any idea later registered from catalogue output must carry
`lineage="catalogue"` unless the chair writes down why not. The sealed batch is registered normally
and counts in `total_trials()`.

## 16. Amendments and chair's notes

- 2026-10-11 (chair): file renamed from the draft and frozen. No grid change.
- **Correction to what the user was told earlier.** The catalogue protocol promised that holding out
  both an unseen era AND unseen coins gives "two chances to fail". For market-wide directional signals
  it does not: two random halves of the coin universe move together (index correlation 0.94), so
  early_B is close to explore's own dates. Directional forms are therefore read on the late era only
  (638 new dates), where the minimum detectable edge is 62-69 bp a day for a raw 1-day state, above
  the 39 bp cost-viable level. Market-neutral forms at 1-3 day holds are the ones the sealed set can
  actually confirm. 129 of the 304 cells are descriptive only.
- The three build preconditions of section 3 (1d gap patch, half-A funding fetch, loader guard with
  planted-row self-test) are NOT done yet. No probe may run until they are, the engine is built with
  its self-tests, and the auditor signs off stage A.
