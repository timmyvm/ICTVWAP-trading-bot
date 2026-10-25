# H020: Residual 14-day momentum, dollar-neutral, top-40 USDT-M perps

**Family:** cross-sectional momentum and reversal (weekly-or-slower rebalance).

**Claim:** Among the ~40 most liquid USDT-M perps, coins that beat the rest of the universe over the
past 14 days, after removing their market beta, keep beating it over the next 14 days. A dollar-neutral
book (long top tercile, short bottom tercile) earns a gross spread of about +55 bp per 14-day rebalance.

## Scout's assessment (read this first)

- The predicted 55 bp is BELOW the chair's ~80 bp bar. At the harness's full-turnover cost (26 bp per
  rebalance) the ratio is 2.1. At the turnover I expect (about 0.65 of each leg replaced per rebalance,
  my estimate, not measured) the cost is about 17 bp and the ratio is 3.2. It clears a 3x test only on
  the second reading.
- Every replication I found on a tradable or liquid perp universe is weak or negative (see Mechanism,
  part 3). The strong published numbers come from wide spot universes.
- Power is poor even if I am exactly right (see Funnel and power).
- Submitted as the baseline of the family and as the comparator for H021, not as a likely winner. My
  subjective chance that a pre-registered test of this card shows a net-positive mean with t >= 2 is
  about 1 in 10.

## Mechanism

**1. Who is on the other side, and why they lose.** Nobody is forced. The candidates are behavioural or
risk-premium. (a) Holders who sell winners early and hold losers, and news-watchers who underreact, are
followed by trend-chasers who overshoot (Hong and Stein 1999, J. Finance; recalled, not re-fetched this
session). (b) The momentum payoff is also compensation for crash risk: after market falls the loser leg
behaves like a written call on the market, so a winner-minus-loser book is crushed in rebounds (Daniel
and Moskowitz 2016, J. Financial Economics, NBER w20439; fetched). Under the scout rules this is the
weakest class of answer to question 1, because no one is forced to trade. I accept it only because the
effect is documented in crypto by several independent teams.

**2. What is documented, and what each paper measured.**
- Liu, Tsyvinski and Wu (2022, J. Finance; NBER w25882 fetched): weekly, value-weighted quintile 5-1
  spreads for 1, 2, 3 and 4-week past return of 2.7, 3.3, 4.1 and 2.5 % per week (t 2.0 to 2.7).
  Sample 2014-2018, 1,707 coins above a $1M market cap, defunct coins included. The paper says it does
  not account for trading costs or the feasibility of short selling. Momentum is stronger above the
  median size (4.2 %/week, significant) than below it (0.6 %, not significant).
- Borri, Liu, Tsyvinski and Wu (2025, arXiv 2510.14435, a preprint; fetched): 2-week momentum factor,
  value-weighted quintile spread 2.6 %/week (t 3.89) in the full sample and 2.1 %/week (t 3.70) after
  2020. Wide spot universe with a $1M floor, no costs, no short-selling analysis.
- Fieberg, Liedtke and Zaremba (2024, Int. Rev. Financial Analysis 94:103218; repository PDF fetched):
  2014-2022, 3,956 coins including dead ones. Momentum alphas are largest in the top 1 to 3 size deciles.
  The alpha comes mainly from SHORT positions (weekly short-leg alphas -1.1 to -1.7 %). With costs of
  30 bp (long) and 40 bp (short), as I read the extracted Table 5, the 2- and 3-week lookbacks survive
  and the 1-week one does not. Second-half alphas are 9 to 76 % lower than first-half ones.

**3. Why I do not extrapolate to tradable perps.** The numbers above are spot, thousands of coins,
value-weighted or small-cap heavy, mostly gross of costs, and the short leg includes dead coins whose
final collapse could not have been shorted. Evidence closest to our universe:
- Arefev (SSRN 7404139, posted 2026-09-10; a preprint by one independent author; I read the abstract
  only): 832 archived Binance perps, 2020-2026. Gross 1-week/1-week spread +0.573 %/week against
  estimated costs of 0.40 pp/week; the net spread is not distinguishable from zero under three tests.
  The 2-week/2-week net spread changes sign with the arbitrary rebalance phase.
- Han, Kang and Ryu (working paper with Internet Appendix, AUT/ACFR site; journal status not verified;
  Binance-futures-listed coins, 2013-2023, shorts via perps, 15 bp cost): cross-sectional momentum is
  "weak". Except for a few large coins most coins show reversal. The short leg suffers jump losses when
  losers rebound. They conclude that steady, market-neutral momentum profit "appears unattainable". They
  say the profit comes mostly from the long leg, which contradicts Fieberg et al. on which leg pays.
- Grobys, Kolari, Sandretto, Shahzad and Aijo (2025, Financial Markets and Portfolio Management; abstract
  and Springer page): top-30 coins, equal-weighted, 2016-2023. Full-sample mean 0.90 %/week is not
  significant. The later period is negative and insignificant. One late-2020 short-leg coin produced a
  crash of about -255 % in a week and a single coin can reverse the whole result.

**4. Why it may persist, and what I expect now.** The limit to arbitrage is risk, not capital: crash
risk and short squeezes in legs of only ~13 names, plus a funding drag on crowded long legs. That limit
is real but it also means the effect is not cheaply removed. Against that, shorting perps is easy and
alt-perp open interest is now large, and Borri et al. report crypto's correlation with equities rising
from about 1 % to 39 % after 2020, a sign of institutional participation. I expect a decayed effect: my
55 bp per 2 weeks is about 0.28 %/week, roughly one-eighth of the post-2020 published value-weighted
figure (2.1 %/week).

## Prediction

- Sign: positive (past 14-day residual winners outperform past residual losers).
- Formation: 14 daily bars. Hold `h` = 14 daily bars. Decision at the close of day t (UTC), fill at the
  open of day t+1, exit at the open of day t+15.
- Number: **+55 bp gross per rebalance** (one long-short pair is one "trade"), hedged, before funding.
  Subjective range -30 to +130 bp.
- Where it comes from: rank IC 0.024 x cross-sectional sd of 14-day residual returns ~10 % x 2.18 (the
  expected z-gap between the top and bottom tercile) = 52 bp, rounded up to 55. The IC is the weekly IC
  implied by Arefev's gross 57 bp/week (assuming a quintile sort and a 12 % weekly cross-sectional sd
  across 832 perps, both MY assumptions) scaled by sqrt(2) for the 2-week horizon. The 10 % sd is my
  prior for 40 liquid perps and the data-engineer should measure it outcome-blind. The number is soft.
- Why 14 and 14: published peaks are at 1 to 3 weeks (LTW, Borri et al., Fieberg et al.), and the
  Dobrynskaya working paper (HSE news summary of the SSRN paper; I did not read the paper) reports the
  strongest payoff at 2-week formation and 2-week holding with reversal appearing at 4 to 6 weeks. Cost
  is charged per rebalance, so I take the longest hold the documented signal life supports. These come
  from prior samples, not from our data.

## Variables (all known at the close of day t, UTC)

Data fields: Binance USDT-M perp daily klines (open, high, low, close, volume, quote_volume, trade count);
8-hourly funding-rate history; the archive's symbol list with first and last file dates. **The full
daily panel is not yet held** (the repo holds 5m klines for 8 coins only, `HANDOFF.md` section 6). Daily
klines are small (one file per symbol-month).

1. `r[i,s]` = ln(close[i,s] / close[i,s-1]).
2. `M[-i,s]` = mean of `r[j,s]` over eligible coins j other than i (leave-one-out equal-weighted universe
   return, so a coin does not hedge itself).
3. `beta_hat[i,t]` = OLS slope of `r[i,s]` on `M[-i,s]` over the 90 days ending at t (at least 60 valid
   days). `beta[i,t]` = 0.5 x `beta_hat` + 0.5 x 1.0 (shrunk toward 1). Reason: Sila, Kristoufek, Mark
   and Weber (2025, Financial Innovation; fetched) find that trailing crypto betas explain only ~20 % of
   next-year beta variation, against ~60 % for US stocks, so raw betas are too noisy to trust.
4. `e[i,s]` = `r[i,s]` - `beta[i,t]` x `M[-i,s]` for the 14 days ending at t.
5. Signal `S[i,t]` = sum of `e[i,s]` over those 14 days.
6. Rank `S` across eligible coins. Long the top `floor(n/3)`, short the bottom `floor(n/3)`. Equal weight
   within a leg, equal dollar notional per leg.

Labelled secondaries (cannot rescue the primary): the same rank on RAW 14-day return (shows how much of
any result is beta); skip the most recent day; 7-day hold; inverse-volatility weights; quintile sort;
rank on distance from the trailing 4-week high (George and Hwang 2004 anchoring; one working paper,
Dobrynskaya, FFA WP 5:003, reports it beats plain momentum for large liquid coins, t 4.93 against 2.33;
I treat it as a secondary because it uses a rolling high, which is level language, and it overlaps
heavily with the primary).

## Universe (point-in-time)

- Symbol list: the archive's own directory listing (every symbol ever listed, with first and last file
  date), never today's exchange listing.
- Eligible at t: onboarded at least 90 days before t; at least 28 of the last 30 daily bars with volume
  above zero; then the top 40 by trailing 30-day median daily quote volume. Membership is recomputed at
  every decision. 40 sits inside the chair's 30 to 50. New listings are excluded for 90 days, which also
  keeps listing-event drift out of this card.
- Exclude index or composite perps (BTCDOM-type, DEFI-type). Map ticker migrations and re-denominations
  explicitly (for example MATIC to POL, 1000-prefixed contracts) so a rename is not read as a delisting
  plus a new listing.
- Survivorship, honestly: a one-symbol spot check of Binance's public archive found the delisted
  original LUNAUSDT daily klines present for 2021-01 through 2022-05, so the archive does keep at least
  some delisted perps. I did NOT retrieve the full symbol list, so completeness is unverified. BTCSTUSDT
  daily files run to 2026-06, so the data-engineer must check whether that is live trading or frozen
  "zombie" rows. The Bybit archive was not checked. A position in a symbol that disappears is closed at
  its last close; these events are counted and reported, because a short in a coin heading for delisting
  is not a fill the real book could have relied on.

## What is neutralised, and how

- **Market beta:** removed from the ranking (residuals against the leave-one-out universe index) and
  checked afterwards. Because beta is poorly predictable, ex-ante neutrality will be imperfect; the
  statistician regresses the realised spread on the universe index AND on BTC and reports hedged alpha
  and both betas as co-primary outputs, using the harness `mkt_ret` argument.
- **Alt-versus-BTC regime:** the universe index minus BTC is a second factor in that regression. Over
  2022-2026 alts broadly lagged BTC (my recollection, not checked against data, which I must not open);
  any book that is net short alt-heavy exposure inherits that.
- **Size and liquidity tilt:** not neutralised ex ante, because the universe is already a narrow
  liquid band. Reported each rebalance as long-minus-short mean log trailing dollar volume, and the
  spread is regressed on it. Secondary: ranks formed within the two liquidity halves.
- Not neutralised: sector or narrative exposure (no labels held).

## Costs and funding

- Primary cost: the harness convention, full turnover, 13 bp per leg round trip, 26 bp per rebalance.
  Also report measured turnover and the turnover-scaled cost as a secondary line.
- Cost sweep at 13, 20 and 30 bp round trip per leg. A flat 10 bp slippage understates the cost of the
  lower-liquidity half of the 40 and of stress days, and book depth only exists from 2023-01, so the
  early years cannot be calibrated. Never report only the friendliest level.
- Funding: real 8-hourly settled funding on both legs for the 14 days held, reported by leg. My
  expectation (unsourced) is that recent winners carry higher funding, so the long leg pays and the
  short leg receives less or pays; I cannot size it without data.
- Short side: no borrow cost on perps; the risk is the squeeze, below.

## Short-leg and tail risk

At equal weights in a 13-name leg, one coin rising +100 % in 14 days costs about 770 bp, which is 14
rebalances of the predicted edge. Required outputs: leave-one-coin-out and leave-worst-week-out means,
winsorised means, the 1st-percentile 14-day return of each leg, and the share of the total P&L from the
best 3 coins. The Grobys et al. and Han et al. results say this is the main way the factor fails.

## Funnel and power

- Decisions: 26 non-overlapping rebalances per year per phase. First eligible date to be set by counting
  eligible names (expected around 2020-H2), so about 6.2 years to 2026-09 and about 160 independent
  14-day observations per phase. About 13 positions per leg.
- Evaluate all 14 daily phase offsets and report the mean and the spread across phases. Do not report
  the best phase. This is the direct lesson of Arefev's sign-flipping result. Using the 14 phases adds at
  most about 30 % effective information, because the tranches overlap.
- Noise (my prior, to be measured outcome-blind): sd of the 14-day spread about 470 bp (13 names per leg,
  ~11 % residual sd per coin, plus a common sector component). Then the minimum detectable true edge at
  80 % power and t = 2 is about 2.84 x 470 / sqrt(160) = 105 bp, and about 160 bp in a 2.7-year verdict
  era. **Both are above my own prediction of 55 bp.** Expected gross Sharpe is ~0.6, which would need ~22
  years of data to detect. If my prediction is exactly right, a test has roughly a 30 % chance of
  showing t >= 2 and a 70 % chance of missing it.
- Better power: the rank information coefficient (or a Fama-MacBeth slope) of `S` against the next
  14-day residual return uses all 40 names, not just 26. The minimum detectable IC is about 0.036 for 160
  periods against my predicted 0.024. Pre-register that as the information test and the tercile spread
  as the economic translation.

## Falsifier

Drop the hypothesis if any of these holds in the pre-registered test:
1. The hedged gross 14-day spread is at or below one full round trip of the book (26 bp), or negative in
   the verdict era.
2. The rank IC is at or below 0.01 in the verdict era (less than half my prediction).
3. The sign of the mean differs across phase offsets (more than 3 of the 14 negative).
4. The result needs one coin or one episode: the mean is at or below zero after removing the best week
   or the best coin.
5. The raw-return version works and the residual version does not. That means the "momentum" was
   market timing through beta, not stock-specific continuation.

## Not claimed

- Nothing about 1-day or 1-week reversal, or about reversal at 4 to 8 weeks.
- Nothing about momentum in small or illiquid coins (the literature says those reverse; they are not in
  this universe).
- No claim about which leg earns the spread (Fieberg et al. say the short leg, Han et al. the long leg).
  The leg split is a diagnostic.
- No claim in bear regimes. Published results are concentrated in bull markets, and I expect weaker or
  negative results in drawdowns; the chair should not judge it on 2021 alone.
- No claim that the fills are achievable for the whole 40 on Bybit; the test uses archive symbols that
  Bybit may list later or not at all.
- No claim about momentum crowding timing (comomentum, Lou and Polk 2022) or volatility-managed scaling
  (Barroso and Santa-Clara 2015); both are extra parameters and neither is in the primary.

## Citation status

Fetched this session: Liu, Tsyvinski and Wu (NBER w25882); Borri, Liu, Tsyvinski and Wu (arXiv
2510.14435, preprint); Fieberg, Liedtke and Zaremba 2024; Han, Kang and Ryu (working paper PDF);
Grobys et al. 2025 (abstract and Springer page); Arefev (SSRN abstract page only); Sila et al. 2025;
Daniel and Moskowitz (NBER w20439); Dobrynskaya (FFA WP abstract, and an HSE news summary of an earlier
paper). Recalled and not re-verified: Hong and Stein 1999, George and Hwang 2004, Barroso and
Santa-Clara 2015, Lou and Polk 2022. Preprints and working papers carrying weight in this card: Arefev,
Borri et al., Han et al., Dobrynskaya. Published, peer-reviewed: Liu et al. (J. Finance), Fieberg et al.
(IRFA), Grobys et al. (FMPM), Daniel and Moskowitz (JFE), Sila et al. (Financial Innovation).
