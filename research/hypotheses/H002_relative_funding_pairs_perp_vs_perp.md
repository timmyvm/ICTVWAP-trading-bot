# H002: Relative-funding pairs. Short the alt perp paying a tail funding rate, long a correlation-matched perp paying the floor or less, no spot leg

## Family and one-line claim

Family: cross-sectional carry on crypto perpetual futures (perp-vs-perp, price leg NOT hedged by
the same asset).

Claim: when an alt's trailing funding is far above the floor, shorting its perp against a long in
the most correlated coin that pays the floor or less earns the funding DIFFERENCE for days, and
that difference exceeds 3x the two-leg round-trip cost. This is the literal structure the family
question asked about (long low or negative funding, short high funding, market neutral) in its
only version that passes the cost bar: tail-gated pairs, not a rank sort. The price leg is an
uncompensated nuisance that the matching shrinks but cannot remove.

**Testability warning, up front.** At the size predicted below the price-leg noise is about 15
times the carry per trade. A net-P&L test cannot resolve it with six years of data (see Funnel).
The card is sent because the user asked for exactly this structure, and because H001 on the same
episodes gives a clean decomposition. The likely statistician verdict is "infeasible on net P&L;
carry component measurable; verdict can only be FAIL or UNRESOLVED". Shelving at Gate 1 is a
legitimate outcome.

## Mechanism

**1. Who is on the other side, and why do they accept it?**
Same payer as H001: small trend-chasing traders buying leverage through the alt's perp, who care
about the price move and not the funding (Schmeling, Schrimpf, Todorov 2023: "trend-chasing and
attention by smaller investors seeking leveraged upside exposure"). The receiver here is a
short-perp holder who is NOT hedged with spot, so he is also paid for bearing price risk.

**2. Why does it persist? (limit to arbitrage)**
- RISK. The pure arbitrage (H001) needs spot, capital and margin. The pair needs no spot and
  little capital, but leaves the relative price of two alts unhedged. The funding difference is
  the premium for bearing that relative price risk, so it is not arbitraged to zero: nobody can
  lock it in. This is a risk premium someone is paid to hold, not a free lunch.
- Possible asymmetry on the long leg (UNSOURCED, mechanism argument only): a positive premium is
  arbitraged by cheap long-spot / short-perp (no borrowing), but a negative premium needs spot
  borrow, which is scarce and costly for alts. So negative or sub-floor funding may persist
  longer, and the long leg may be paid more reliably than the short leg. The statistician reports
  the two legs' funding separately; it is a pre-declared decomposition, not an extra trial.
- Capacity: same as H001. Tail alts are small; a fund cannot deploy; a small book can.

**3. What the price leg is expected to do, and why I credit it zero.**
The sources point in opposite directions, so I claim no sign.
- Against the short leg (momentum): Liu, Tsyvinski, Wu, "Common risk factors in
  cryptocurrency", Journal of Finance (2022), NBER w25882. Measured: spot coins on
  CoinMarketCap, market cap above $1 million, 2014-2018 (1,707 coins in total), gross returns
  (I could not confirm their portfolio weighting from the pages I read). Only 1-4 week lookbacks
  give significant continuation (winners minus losers 2.7%, 3.3%, 4.1%, 2.5% a week); stronger
  in above-median size coins (4.2% a week) and insignificant in below-median (0.6%). He, Manela,
  Ross, von Wachter (preprint) find past returns explain the perp-vs-spot gap, so the
  high-funding set is mostly recent winners. A short in recent winners against a long in a
  floor-funded coin loads on that continuation.
- For the short leg (crash risk): Schmeling et al. find a high carry predicts price crashes,
  measured on BTC and ETH futures, not alt perps, and not a mean return.
- Short horizon reversal: Zaremba, Bilgin, Long, Mercik, Szczygielski, International Review of
  Financial Analysis 78 (2021): over 3,600 coins, previous-day losers beat winners, tied to
  illiquidity, but the largest and most tradeable coins show daily MOMENTUM. Mostly spot
  micro-caps; partial transfer to liquid perps.
- Net: no defensible sign. The headline number credits the price leg zero; the matched partner
  is chosen only to shrink its variance.

**4. Primary documentation.** Same as H001: Binance funding FAQ and Bybit help-centre funding
articles. Funding is censored at the floor: `F = I = 1 bp` for P in [-0.04%, +0.06%], and
`F = P - 5 bp` above. A whole-universe rank sort therefore compares mostly ties.
Why not a quintile sort (prior arithmetic, UNSOURCED numbers): in a quiet period the top quintile
may sit only 0.5-1 bp above the floor, so a 14-day pair earns 21-42 bp against a 26 bp full
round trip (ratio about 1); in a hot period the spread may be 3-5 bp, earning 126-210 bp (ratio
5-8). The unconditional average is under the 3x bar. Gating on the tail keeps only the hot part,
which is H001's state. That is the whole reason this card is a tail-gated pair.

**State, not location (Q3).** The state is "excess funding is large and the matched partner pays
the floor or less".

## Prediction

- Sign: positive for short alt perp / long partner perp, on the funding component. The price leg
  carries no sign.
- Horizon: bar = one 8 h funding interval (decisions at 00:00, 08:00, 16:00 UTC after the print).
  Expected hold 42 bars (14 days) for the fixed-horizon information test; exit by rule.
- Expected gross excess per trade: **about +80 bp per pair of short-leg notional, that is about
  40 bp per leg**, all of it funding difference. The price leg is credited zero.
- Where the number comes from: entry when the net funding difference
  `G = F_bar_short - beta x F_bar_long` is at least G* = 5 bp per 8 h; exit when G falls to 1.3
  bp; half-life of the excess 5 days (15 settlements, UNSOURCED, measured at Gate 1). Collected =
  5 x 15.7 = 78 bp. G* solves 3 x C_pair = G* x L, with C_pair = 13 x (1 + beta) = 26 bp at
  beta = 1 and L about 15.7 settlement-equivalents. The exit level is the user's 14.5% a year
  hurdle expressed per settlement on capital (1.32 bp), with capital per unit short notional of
  about 1.0 (two margin legs at 2x).
- Cost ratio 78 / 26 = 3.0 against the pair, right at the bar and no better. Same slippage
  warning as H001: 1 bp per side is a BTC-grade number; a thin alt costs more, and here BOTH legs
  trade.
- Sensitivity to the half-life, as in H001: 2.5 days about 40 bp (1.5x, fails), 10 days about 150
  bp.
- Price-leg size (assumption): two alts at 80% annual volatility with correlation 0.7 give a pair
  volatility of about 62% a year, so about 12% (1,200 bp) over 14 days. Carry to noise about
  1 : 15.

## Variables (all computable at the close of the decision bar t, UTC)

Data fields: as H001 for funding (`fundingRate` with interval column), plus daily closes from
USDT-M klines for the 60-day correlation and beta. Data status: **not held beyond 8 coins** (see
H001). No spot data needed. Depth from 2023-01 for the cost stress.

- `F_bar_i,t`: trailing 24 h mean of per-8 h-equivalent funding, exactly as in H001.
- Short candidate: coin i with `F_bar_i,t - I >= X*`, where I = 1 bp and X* is set by the G*
  arithmetic above (about 5 bp when the partner pays the floor).
- Partner set: coins j with `F_bar_j,t <= I` (paying the default or less, including negative).
  This uses the floor itself as the threshold, so there is no free parameter.
- Partner choice: the coin j in that set with the highest correlation of daily log returns with i
  over the previous 60 days (ending at t, point-in-time). Reason for 60 days: long enough for a
  stable beta, short enough relative to a 14-day hold; the statistician fixes it.
- Hedge ratio: `beta_ij` = OLS slope of i's daily log returns on j's over the same window,
  clipped to [0.5, 2] (noisy betas beyond that are not trusted). Long notional = beta x short
  notional.
- `G_ij,t = F_bar_i,t - beta_ij x F_bar_j,t`. Enter at `G >= G*`; exit at `G <= G_exit`, or on
  delisting. One pair per short coin; a partner may serve several shorts.
- Sizing: at most K = 5 pairs, each pair at most 20% of equity gross per leg, perp leverage at
  most 2x per leg. (Pair-level diversification is the only variance reducer available.)
- Fills at the open of the first minute bar after the decision close. Funding on each leg at
  the actual settlement rates (the long leg RECEIVES negative funding).
- **Sign trap for the builder.** The short leg receives positive funding, the long leg pays it.
  Test with a planted two-coin panel whose answer is known by hand.
- Decomposition pre-declared (not extra trials): funding on the short leg, funding on the long
  leg, price leg, costs. And H002 minus H001 on matched episodes (same coin, same dates) = the
  pure price-leg cost of hedging with a perp partner instead of spot.

## Universe

Identical to H001 except that no spot market is needed, so the eligible set is larger (more
tail names, including perp-only listings). Point-in-time monthly reconstitution on prior-day
data, Binance USDT-M, at least 90 days of history, ranks 3-50 by trailing 30-day median turnover,
delisted symbols INCLUDED (a delisting with an open leg is closed at the last print and reported
separately), exclusions as in H001. Partner coins must come from the same reconstituted list.
Bybit tradability of both legs is required on the entry date.

## Funnel estimate

Outcome-blind prior, to be replaced by counts: the episodes of H001 plus those without spot, so
**about 30-60 pairs a year, 180-360 over 2020-09 to 2026-08**, concentrated in the same few
euphoric months. Date-clustered independent episodes are fewer, perhaps 80-150 in total.

Power (assumptions): N required to resolve 80 bp at 2.8 sd = (2.8 x 1,200 / 80)^2 = **about
1,760 independent pair-trades**. Even with a tighter partner match at sd 800, about 780. Available:
180-360, clustered. Minimum detectable mean at N = 300 and sd 1,200 is about 194 bp, 2.4 times the
prediction. **A net-P&L test cannot confirm this card.** What CAN be done: (1) the realised
funding difference per pair is a near-deterministic cash flow and can be compared with 3 x 26 bp
with a tight interval; (2) the price leg can only be bounded below (with N = 300 its standard
error is about 69 bp, so a one-sided bound excludes only price-leg means worse than roughly -150
bp); (3) the H002 minus H001 difference is the cleanest estimate of the price leg and is still
noisy. The honest outcomes are FAIL or UNRESOLVED, never PASS.

Gate 1 data report: same as H001 plus (g) the realised volatility of matched pairs against
unmatched alt-vs-BTC, outcome-blind, to see whether correlation matching actually shrinks the
price leg.

## Falsifier

Drop the card if any of these hold:
1. `power.feasible` for the registered edge and sd returns not ok (expected). Record it and shelve
   rather than spend a verdict-era look.
2. Gate 1: the tail half-life is under about 3 days, or the realised mean funding difference per
   pair is under about 55 bp (then it is under 2x cost before any price effect).
3. Matching fails: realised pair volatility over the hold is not materially below that of an
   unmatched alt against BTC. Then the card is a directional alt bet with a funding tilt.
4. The price leg is clearly negative on the freshest block: mean price leg per pair below about
   -100 bp, or the H002 minus H001 difference significantly negative. Momentum on the short leg
   (Liu et al.) has then eaten the carry.
5. Cost stress with depth-derived slippage on both legs pushes the pair cost above about 45 bp.
6. The episodes are the same as H001's and add nothing: if H001 is run and fails on half-life or
   decay, H002 inherits the failure.

## Not claimed

- No sign for the price leg. The headline number credits it zero.
- No claim that a net-P&L test is feasible. The card says it is not.
- No whole-universe quintile sort (censored funding, ties, ratio near 1 on a prior; see
  Mechanism 4).
- No timing of BTC/ETH, no settlement-flow effect (v0.24), no directional alt view.
- No claim about the negative-funding long leg being more reliable; that asymmetry is an
  unsourced mechanism argument that the leg-level decomposition can inform but not prove.
- No maker fills, no rebates.
- Correlated-trial warning: H001, H002 and H011 trade the same tail-funding states. H011 is the
  time-series, single-coin fader of the same crowd (it claims a price leg); H002 deliberately
  claims none. If both are run, count them as correlated trials.
