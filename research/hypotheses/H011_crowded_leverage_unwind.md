# H011: Crowded-leverage unwind. Fade the side that is paying an extreme upcoming funding rate while still adding positions without price progress

## Family and one-line claim

Family: forced-flow states on crypto perpetual futures (funding extreme, open-interest build,
crowding).

Claim: when the upcoming funding rate is extreme against one side, open interest has been
building in the last few days, and price has NOT advanced for that side, the crowded side is
fragile and the next 48 hours carry a heavier left tail for it. Trade against the crowd (short
after crowded longs, long after crowded shorts). This is a fade-the-crowd claim, made BEFORE the
unwind starts: it predicts continuation of the adverse move for the crowd. It is the mirror of
H010, which predicts reversal AFTER the unwind has ended.

**Testability warning, up front.** At the size predicted below this card is under-powered by
construction on a mean-return test (see Funnel). It is sent because the family question asks
about exactly this state, and because a tail-frequency version of the test may be feasible. If the
statistician finds it infeasible, shelving it is the right answer.

## Mechanism

**1. Who is on the other side, and why do they lose or accept it?**
- The crowd: small, trend-chasing traders using leverage to get upside exposure. They pay the
  funding rate on notional every 8 hours. At 0.05% per 8 h that is about 55% a year on
  notional, which is only recouped if the coin rises by more than that. Their payment goes to
  the short side, mostly basis traders (long spot, short perp) who are hedged and are paid for
  supplying leverage.
- The youngest open interest is the most fragile. Positions opened in the last days at high
  leverage have had no time to build a margin cushion, so their liquidation prices sit a few
  percent from the current price. Older positions have either built a cushion or already been
  closed out. That is why the state asks for OI BUILT recently and price that has NOT moved in
  the crowd's favour: the build is un-cushioned. (This is my reasoning, unsourced.)
- The directional counterparty (the fader) accepts squeeze risk, and in a trend the crowd is
  right for weeks. The claim is only about the tail, not the average day.

**2. Why does it persist? (limits to arbitrage)**
- Arbitrage capital is scarce and cash-and-carry is itself risky because margin spikes and
  liquidations arrive in drawdowns, so the price of leverage stays large and time-varying.
  Schmeling, Schrimpf, Todorov, BIS Working Paper 1087 (2023), also CEPR DP20719 (2025): carry can
  reach about 60% a year, is attributed to small trend-chasing investors seeking leveraged upside
  plus scarce arbitrage capital, and "a high crypto carry predicts future price crashes".
- What that source does and does not show. I read the BIS summary page only, not the paper body.
  It covers BTC and ETH futures; the summary never mentions perpetual swaps or funding rates and
  gives no horizon for the crash prediction and no effect size. The CEPR page lists it as a
  discussion paper with no journal publication shown, so treat it as unrefereed. It supports
  "high leverage demand with scarce arbitrage capital precedes crashes". It does NOT show that a
  perp funding rate plus an OI build predicts a 48 h left tail, which is this card's actual claim.
- The funding mechanism is documented: Binance's FAQ gives funding as the average premium index
  plus a clamp of (interest rate minus premium) at plus or minus 0.05%, interest 0.01% per 8 h.
  He, Manela, Ross, von Wachter (arXiv 2212.06888, preprint, v6 2024) derive no-arbitrage perp
  prices and find deviations larger than in FX; nothing there predicts returns.
- Honest counter-argument: in a bull trend, funding stays extreme for weeks while price rises.
  A fader who shorts every extreme loses to the trend. The price-progress condition is the
  attempt to exclude those cases; if it fails to, the card dies.

**3. Why the upcoming rate and not the last settled one.** CLAUDE.md lesson: traders react to the
payment they are about to make. The last settled rate (v0.24's primary) is the wrong variable.
Also, funding is CENSORED. Binance's formula gives `F = P + clamp(I - P, -0.05%, +0.05%)`, so
whenever the average premium P lies between -0.04% and +0.06% per 8 h the funding rate is
exactly the 0.01% interest component and carries no information. Funding only differs from
default when the premium is already beyond about 0.06%. The premium index itself keeps varying
inside that band and is the better continuous state.

**4. Not already dead.** v0.24 tested last-settled funding around the settlement, effect 1-5 bp.
v0.18 funding carry (delta-neutral) passed at about 10-14% a year. This card is a directional
state at 48 h conditioned on the UPCOMING rate and an OI build. It is not the settlement flow and
not a delta-neutral carry. The funding it collects (see Prediction) is the same stream carry
harvests, so the test must show the price leg does not eat it.

**State, not location (Q3).** No level is drawn.

## Prediction

- Sign: against the crowd. Crowded-long state (F_hat extreme positive) means SHORT. Crowded-short
  state (F_hat extreme negative) means LONG.
- Horizon: h = 48 bars of 1 h (six funding settlements at the 8 h interval).
- Expected gross PRICE excess per trade to the fader (vs the drift-matched unconditional 48 h
  return of the same coin, signed so that a profit for the fader is positive): **+50 bp** in the
  liquid-alt tier. BTC/ETH about +25 bp, which is BELOW the 40 bp bar on the price leg alone.
- Funding received by the fader, shown separately because the repo's bar is price excess before
  funding: at the anchor of 0.05% per 8 h over six settlements, about +30 bp. With it, the total
  is about 80 bp for alts and 55 bp for BTC/ETH.
- Where the +50 bp comes from (an ASSUMPTION, not a measurement): the state raises the
  probability of a 15% adverse move within 48 h by about 4 percentage points, and 4% of 1,500 bp
  is 60 bp, rounded down. The BIS result says only that carry predicts crashes; the 4 points is
  mine.
- Cost ratio on price alone: 50 / 13 = 3.8 (alts); including funding 80 / 13 = 6.

## Variables (all computable at the close of the decision bar t, UTC)

Data fields: 1 m `premiumIndexKlines` (Binance USDT-M archive); 5 m klines; daily `metrics`
(`sum_open_interest`); `fundingRate` history and the funding-interval/cap information per symbol.
Data status: **premium-index klines, metrics files and funding-interval information are NOT yet
held.** The data engineer must check whether some alts moved to 4 h or 1 h funding intervals and
whether caps changed; the weights below assume an 8 h window. Restrict to 8 h-interval periods if
needed.

- Premium sample `p_m`: close of the m-th 1 m premium-index kline since the last settlement
  (00:00, 08:00, 16:00 UTC), m = 1..n_e at decision time (n_e minutes elapsed).
- Running premium estimate `P_hat_t`, built from Binance's documented rule that later samples
  carry linearly increasing weights over the 8 h window (Binance samples every 5 s, 5,760 slots;
  the 480 one-minute slots below are a coarser version of the same weighting). Carry the latest
  observation forward over the unseen remainder:
  `P_hat_t = [sum_{m=1..n_e} m * p_m + sum_{m=n_e+1..480} m * p_{n_e}] / sum_{m=1..480} m`.
  This uses no future data; the carry-forward is a persistence forecast of the remainder.
- Upcoming funding `F_hat_t = P_hat_t + clamp(I - P_hat_t, -0.05%, +0.05%)`, with I = 0.01% per
  8 h, then limited by the symbol's floor and cap (about plus or minus 2% for most alts, and
  0.75 times the maintenance margin ratio for BTC, ETH and a few others).
- Extreme: `F_hat_t >= F*` (crowded long) or `F_hat_t <= -F*` (crowded short). Anchor for the
  scale: F* = 0.05% per 8 h, five times the interest component and about 55% a year on notional,
  where the funding bleed on leveraged margin is material and the return to a hedged arbitrageur
  is far above any cash rate, so the limit on arbitrage capital is clearly binding. The
  statistician fixes the grid around it. Because of the censoring, also define the premium-based
  state `P_hat_t >= 0.06%` (the first point where funding leaves its default).
- OI build: `dOI72_t = ln(OI_t / OI_{t-72h})` (coin units, from `sum_open_interest`, latest row
  stamped at or before t minus 5 minutes) in the upper tail of that coin's own point-in-time
  distribution of 72 h changes. Reason for the scale: three days is about the age at which new
  leveraged positions have not yet built a cushion or been closed.
- Price progress: `R72_t = ln(P_t / P_{t-72h})`, and the crowd side is not winning, i.e.
  `R72_t <= c * sigma_i * sqrt(72)` for the crowded-long case (mirror for crowded-short), with
  sigma_i the 1 h return standard deviation over the 30 days before the window and c at most about
  0.5. Reason: a cushion matters relative to the typical liquidation distance of 1/L (3-10% for
  10-30x leverage), so the statistician should map c to that distance per coin.
- Secondary conditioners (ablations, not in the primary): the Binance global long/short account
  ratio and the top-trader position ratio, from the same metrics file; and OI divided by
  trailing 30-day turnover as a leverage-per-liquidity proxy for the thin-coin tier.
- Exit: 48 h later. One entry per coin per 48 h.

## Universe

Same point-in-time construction as H010: Binance USDT-M perps with at least 90 days of history;
Tier A = ranks 3-40 by trailing 30-day turnover as of t-1 day (primary); Tier B = BTCUSDT and
ETHUSDT (control); Tier C = ranks 41-120 (secondary). Include later-delisted symbols. Extreme
funding sits mostly in alts and in euphoric periods, so a pooled sample will be dominated by a
few bull-market stretches; report era blocks.

## Funnel estimate

Outcome-blind arithmetic, to be confirmed by counts (no P&L needed). Extreme upcoming funding,
an OI build and non-confirming price together are a conjunction of three tails. Estimate: 0.5-2%
of coin-days meet the funding anchor in the alt tier, a third to a half of those also have an OI
build, and a third of those have non-confirming price, giving about 20-120 coin-days a year.
After the 48 h cooling and de-clustering: **15-60 entries a year, and only about 10-30
date-independent events** because extreme funding clusters in euphoric weeks. Over 2020-09 to
2026-08 that is roughly 60-350 entries.

**BTC/ETH on their own: a handful of qualifying days a year, strongly autocorrelated, perhaps 2-5
independent events a year and 15-30 in total. Too rare to ever test alone.**

Power (assumption: 48 h trade sd about 1,000 bp in alts): the minimum detectable mean effect is
about 2.8 * 1,000 / sqrt(200) = 200 bp at 200 independent events, four times the predicted 50 bp.
**A mean-return test cannot resolve the claim.** A frequency test of the left tail does better
but is still marginal: if the base rate of a 48 h move of 2 standard deviations or worse against
the crowd is about 2.5% and the state doubles it to 5%, 300 events give a standard error near 1.3
percentage points on the state's rate, so the 2.5-point gap is only about 2 standard errors, and
fewer once events are clustered by date. The statistician should consider a tail-frequency
primary (mechanism test) with the net mean (price plus funding) as the economic check. If neither
is feasible, shelve.

## Falsifier

Drop the card if any of these hold:
1. The probability of a 48 h adverse move of 2 standard deviations or more in the crowded
   states is no higher than the drift-matched base rate, on the freshest untouched block.
2. The mean price leg of the fader is negative and larger than the funding it collects (the
   trend wins), in the held-out era or in two of three era blocks.
3. The effect disappears when the upcoming rate F_hat is replaced by the last settled rate
   (then it was never about the payment about to be made), or it is the same with the OI-build
   condition removed (then it is just a funding extreme, which v0.24 and v0.18 already cover).
4. Adding the Binance long/short ratios, or varying the price-progress condition, flips the
   result's sign: that would show the sign depends on a nuisance filter.

## Not claimed

- No claim that funding extremes predict the average 48 h return, only the left tail for the
  crowded side.
- No claim about the settlement-time flow around the funding timestamp (v0.24).
- No claim that the long/short account ratios or top-trader ratios carry "smart money" or
  contrarian information. They appear only as ablations. RESEARCH.md section 5 trap: no source
  was found for either reading; web search returned vendor dashboards and news only.
- No claim for BTC/ETH on the price leg: predicted +25 bp is under the bar, and the events are
  too few anyway.
- No claim at horizons outside 24-72 h.
- A cross-sectional ranking version (long low funding, short high funding, dollar-neutral) is
  the carry scout's territory. This card is the time-series, state-conditioned counterpart and
  adds the OI-build and price-progress conditions. If both are run, the statistician should
  count them as correlated trials.
