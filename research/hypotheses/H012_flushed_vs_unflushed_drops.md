# H012: Flushed versus unflushed drops. Among coins that all fell hard, leverage removal decides who rebounds

## Family and one-line claim

Family: forced-flow states on crypto perpetual futures (open-interest collapse versus
open-interest retention after a large drop).

Claim: on a day when several liquid perps have each fallen far, the ones whose open interest
collapsed (leverage flushed) outperform over the next 24 hours the ones whose open interest held
or grew (crowd still positioned and underwater). Trade the contrast: long the most flushed, short
the least flushed, equal notional. This card is the forced-flow-specific, market-neutral test of
the mechanism behind H010, and it supplies the sign of the "no flush" state that H011 argues is
fragile. Claim type: REVERSAL for the flushed leg, weak CONTINUATION (relative) for the unflushed
leg.

## Mechanism

**1. Who is on the other side, and why do they lose?**
- Flushed coins: the sellers were forced or panicked (margin calls, then capitulation). Their
  flow is non-informational and its price effect is temporary. Same mechanism and sources as
  H010 (Coval and Stafford 2007; Nagel 2012; Brunnermeier and Pedersen 2009).
- Unflushed coins: the price fell while open interest stayed. Either new shorts opened (a
  speculative, position-creating flow, which Llorente, Michaely, Saar, Wang 2002 argue tends to
  continue because it carries information), or old longs sat tight. Those longs are still
  holding and are underwater, so the fuel for a later forced unwind is still there (H011's
  argument; unsourced for crypto). Expectation: no reversal, or a smaller one.
- The pair also removes the most common source of noise in H010, the market direction.
  Both legs are coins that fell on the same day, so BTC's next-day move hits both about equally.

**2. Why does it persist?**
Same limits to arbitrage as H010 (intermediary capital withdraws in stress; capacity is small;
inconvenience for large funds), plus one more: a market-neutral pairs trade on perps needs two
positions at once and a ranking across 50 or more contracts, which is a nuisance for a manual
trader and a small prize for a fund.

**3. Analog and its limits.** Coval and Stafford (2007) also trade both sides of forced flow: they
buy stocks sold by flow-constrained funds and short stocks those funds were forced to buy, and
report large annualised abnormal returns in calendar time (their Table 5, roughly 28-45% a
year, t about 3-5, 95 feasible months, ignoring the cost of capital while waiting). I read the
paper at table level. It is monthly, in equities, and its short leg is "forced buying", not
"unflushed selling", so it supports pairing the two sides of forced flow, not this exact rule.
Zaremba et al. (2021, IRFA 78) find ordinary daily reversal across illiquid coins and
momentum among the largest. If ordinary illiquidity reversal were the whole story, flushed AND
unflushed drops would both revert and this spread would be about zero. That makes H012 the card
that separates "forced flow" from "illiquidity reversal". Data caveat as in H010: Giagkiozis and
Said (*Ledger* 2024) show reported OI can be unreliable; inferred forced flow is an assumption
(no liquidation feed).

**State, not location (Q3).** The conditioning is a ranking of OI changes across coins; no level
is drawn.

## Prediction

- Sign: long the most-flushed tercile, short the least-flushed tercile of the day's set of large
  fallers.
- Horizon: h = 24 bars of 1 h, one decision per UTC day at the 00:00 close. The fixed daily time
  is a sampling convention to avoid overlapping holds; it carries no time-of-day claim.
- Expected gross excess per pair-trade (long-leg minus short-leg drift-matched 24 h return):
  **+100 bp, per unit of long notional.** Components: long leg +70 bp, short leg +30 bp
  (the short earns because the unflushed coins do not rebound as much, or fall further).
- Where it comes from (ASSUMPTION): the long leg is H010's +100 bp discounted by about 30%
  because a fixed daily clock does not wait for the completion condition; the short leg is a
  guess at a modest continuation for coins whose crowd is still in. No measurement exists.
- Cost: two legs, 26 bp round trip per unit of long notional. Cost ratio 100 / 26 = 3.8,
  at the margin of the 3x rule. Alt slippage after a selloff is wider than 1 bp a side, so run
  a cost schedule by liquidity tier. Funding on both legs is charged by the harness.

## Variables (all computable at the close of the decision bar t = 00:00 UTC)

Data fields: 1 h perp closes (from 5 m klines) and `sum_open_interest` (metrics). Same data
status as H010: **metrics files and most of the universe's klines are NOT yet held.**

- `R_t = ln(P_t / P_{t-24h})` and `sigma_i` exactly as in H010 (30 days before the window).
- Large faller set `D_t`: coins with `R_t <= -max(k * sigma_i * sqrt(24), 5%)`, the same k as
  H010 (no new parameter). Require `|D_t| >= 6` so each tercile holds at least two coins.
- `dOI_t = ln(OI_t / OI_{t-24h})` in coin units, from the latest metrics row stamped at or before
  t minus 5 minutes.
- Rank `D_t` by `dOI_t`. Long the lowest third (most flushed), short the highest third, equal
  weight per coin and equal gross per leg. BTC and ETH are excluded from the legs and used only
  for beta.
- Exit at t + 24 h. No cooling needed because there is one decision a day, but a coin held on
  one day is not re-entered the next day (overlap guard).
- Secondary (cannot rescue the primary): a continuous version that regresses next-24 h excess on
  the within-day OI rank over all of `D_t`; the same contrast on large RISERS (short the
  OI-collapsed, long the OI-built) with the caveat that its long leg is exposed to H011's
  crowding fragility; the contrast with the H010 completion condition imposed on the long leg.

## Universe

Binance USDT-M perps, point-in-time: ranks 3-60 by trailing 30-day median daily USDT turnover as
of t-1 day (wider than H010 because the contrast needs enough fallers on one day), at least 90
days of history, later-delisted symbols included, index and delivery contracts excluded. If the
archive lacks delisted symbols the data report must say so, because the long leg is exactly where
death-spiral coins appear.

## Funnel estimate

Outcome-blind arithmetic, to be confirmed by counts. If a coin has about a 3-6% chance on any
day of falling by the size floor, a 58-coin universe has 2-3 qualifiers on an average day, but
qualifiers are market-clustered, so days with six or more are selloff days: roughly **15-35
decision days a year, 90-200 over 2020-09 to 2026-08**, and the independent episodes are fewer
(perhaps 6-12 a year) because selloffs last several days.

Power (assumption: sd of a daily pair spread about 550 bp): the minimum detectable effect is
about 2.8 * 550 / sqrt(150) = 126 bp at 150 decision days, above the predicted 100 bp. **The
central prediction is marginal on the full sample and unresolvable on a one-year verdict era.**
The statistician may prefer the continuous within-day rank regression, which uses all of `D_t`
and has more power. What this design buys is a smaller sd than H010's directional trade, not
more events.

## Falsifier

Drop the card if any of these hold:
1. The pair spread, measured from the first tradable price after t, is at or below 26 bp on the
   freshest untouched block, or has the wrong sign in two of three era blocks.
2. Flushed and unflushed fallers revert by about the same amount. Then OI is not the
   discriminator, the reversal (if any) is ordinary illiquidity reversal, and forced flow is the
   wrong mechanism. A short-term reversal strategy may still exist but belongs to the
   cross-sectional reversal scout.
3. The spread comes almost entirely from beta mismatch: hedged alpha after the BTC beta is not
   positive with t of about 2.
4. The result flips sign when OI measured in USD value replaces OI in coin units (then it is a
   price artifact, not a position artifact).

## Not claimed

- No claim about market direction. The pair is built to be indifferent to it.
- No claim on days with fewer than six large fallers.
- No claim for BTC or ETH. They are not in the legs.
- No claim that unflushed fallers keep FALLING in absolute terms; only that they rebound less
  than the flushed ones.
- No claim about large risers beyond the labelled secondary.
- Not independent of H010. They share the flush state and the long leg's mechanism, so the
  statistician should count them as correlated trials, and if only one can be afforded, H012 has
  the lower noise and H010 the higher event count.
