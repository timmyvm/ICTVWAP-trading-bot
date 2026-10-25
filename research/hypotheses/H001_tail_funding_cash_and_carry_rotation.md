# H001: Tail-funding cash-and-carry rotation. Hold long spot / short perp only on the few alts whose funding is far above the floor, and leave when it falls back

## Family and one-line claim

Family: cross-sectional carry on crypto perpetual futures (spot-vs-perp, price leg hedged).

Claim: among 30-50 point-in-time liquid USDT perps, the few coins whose trailing-24 h funding is
far above the 1 bp per 8 h floor keep paying it for days (leveraged-long demand persists faster
than arbitrage capital arrives). A long-spot / short-perp position opened on those coins and
closed when funding falls back toward the floor collects more than 3x its two-leg round-trip cost.
The price leg is hedged by the spot leg and is a nuisance, not a claim.

This is NOT v0.18 (single-coin BTC/ETH carry held continuously) and NOT v0.24 (settlement flow).
The only new object is the cross-sectional choice of WHICH alts to hold and WHEN. I have not seen
why v0.18's "timed" variant failed (I may not look at results). If it failed because BTC/ETH
funding almost never leaves the floor, the alt tail is the untested part; if it failed because
funding episodes do not persist, this card fails the same way, and the Gate 1 half-life check
below will show it before any trade is simulated.

## Mechanism

**1. Who is on the other side, and why do they accept it?**
- Small, trend-chasing traders who buy leverage through perps and pay funding on notional every
  settlement. Schmeling, Schrimpf and Todorov (2023) attribute crypto carry to exactly this:
  "trend-chasing and attention by smaller investors seeking leveraged upside exposure" plus
  scarce arbitrage capital. They accept the payment because they want the price move, not the
  carry, so the payment is not what they optimise. The payer is paying a price for leverage.
- The receiver is whoever is short the perp and hedged long spot (a basis trader). That is the
  position this card holds.

**2. Why does it persist? (limits to arbitrage)**
- Capital and margin. The cash-and-carry needs the full spot notional plus perp margin. The
  CEPR VoxEU summary of Crypto Carry (not the paper body) says that on CME, where spot Bitcoin
  cannot be posted as futures collateral, a cash-and-carry at 10x leverage would have had its
  short futures leg liquidated in more than half the months of the sample. That is a CME,
  BTC/ETH, fixed-maturity statement. Alt perps are far more volatile, so the leverage the short
  leg can safely carry here is lower and the capital need higher; that is my inference, not theirs.
- Margin-based limits to arbitrage in general: Garleanu and Pedersen (RFS 2011) show that when
  margins bind, securities with identical cash flows trade at persistent gaps ("bases") that
  depend on relative margins. Theory, not crypto; used only for the direction of the argument.
- Capacity and inconvenience. Tail-funding alts have small open interest and thin spot books. A
  fund cannot deploy meaningfully; a book of tens of thousands of dollars can. This is the
  "too small for large funds to bother with" case.
- Counterparty risk (exchange failure) is not diversifiable by the trade and no backtest shows it.
- Honest counter-evidence on persistence of the edge itself: Crypto Carry reports carry fell
  sharply after the spot Bitcoin ETFs launched, and He, Manela, Ross and von Wachter find
  perp-vs-spot deviations shrinking about 11% a year (preprint, below). Arbitrage capital is
  arriving. CLAUDE.md lesson: the era is the variable.

**3. Why the signal lives in the tail only (primary-source arithmetic).**
Binance's funding FAQ and Bybit's help-centre article give the same rule: with I = 0.01% per 8 h
and P the time-weighted average premium index,
`F = P + clamp(I - P, -0.05%, +0.05%)`.
Whenever P is between -0.04% and +0.06% per 8 h, F is exactly I = 1 bp. Binance states this in
words. Outside that band F = P - 5 bp (above) or P + 5 bp (below). So funding is CENSORED:
for most coin-settlements it is a constant, a cross-sectional sort of the whole universe compares
mostly ties, and the paid carry above the floor exists only for coins in the tail. That is why
the design is a threshold on excess funding, not a quintile sort. (H011, written in parallel,
reaches the same censoring point for the time-series fader.)

**4. Sources, and what each actually measured (RESEARCH.md section 5 check).**
- Schmeling, Schrimpf, Todorov, "Crypto Carry", BIS Working Paper 1087 (April 2023); the INFORMS
  page lists it in Management Science (year not shown on the page I could read). I read the BIS
  landing page and the CEPR VoxEU column, NOT the paper body. Measured: BTC and ETH fixed-maturity
  futures (1- and 3-month), main series OKEx, March 2019 to July 2024, plus CME and ETF analysis.
  NOT perpetuals, NOT alts, NOT a cross-section. Claims used: carry averages above 10% a year in
  the working paper and spikes above 40-60%; fundamentals do not explain it; small-investor
  leverage demand and scarce arbitrage capital do; a high carry predicts price crashes (WP).
  The VoxEU column also says a rise in standardised carry predicts higher forced-liquidation
  volume relative to open interest over the next month (its wording on which side is liquidated is
  inconsistent, so I do not rely on the direction).
- He, Manela, Ross, von Wachter, "Fundamentals of Perpetual Futures", arXiv 2212.06888 (v6, Aug
  2024). PREPRINT, no journal listed. Measured: BTC, ETH, BNB, DOGE, ADA on Binance, hourly,
  January-July 2020 to 11 March 2024. Claims used: mean absolute deviation from the no-arbitrage
  price of 60-90% a year, comoving across coins, falling about 11% a year; past returns explain the
  gap; a threshold arbitrage earns Sharpe 1.8 for BTC under retail fees. One summary I saw says
  most of that return came from basis convergence rather than funding payments; I could NOT verify
  that in the paper text (tool returned only the theory sections). Treat it as a lead for the
  statistician to read in section 4.3, not as evidence.
- Koijen, Moskowitz, Pedersen, Vrugt, "Carry", JFE (2018), NBER w19325. Expected return =
  carry + expected price appreciation, carry predicts returns across asset classes. Not crypto.
  Used only to frame the decomposition: the claim here is the carry part, with the price
  appreciation part hedged away.
- Exchange documentation: Binance funding FAQ (formula, dead zone, intervals, caps), Bybit
  help-centre funding articles (same formula, interest I = 0.03% / (24 / interval), interval can
  switch to hourly when the cap is hit), Bybit fee page (spot 0.1% / 0.1%, perp 0.02% / 0.055%).
- Not used as evidence: practitioner dashboards and exchange-published research.

**State, not location (Q3).** The state is "the funding actually paid over the last day is far
above the floor". No drawn level.

## Prediction

- Sign: positive for long spot / short perp on the qualifying coin.
- Horizon: bar = one 8 h funding interval (decisions at 00:00, 08:00, 16:00 UTC, right after the
  settlement prints). Expected hold about 21 bars (7 days); the rule-based exit decides the actual
  hold. For the harness's fixed-horizon information test use h = 21 bars.
- Expected gross excess per trade: **about +110 bp of spot notional**: roughly 105 bp of funding
  collected plus roughly 5 bp of basis convergence. Funding IS the payoff in this family, so this
  "gross" includes it and excludes only trading costs (the generic 40 bp rule says "before funding"
  and does not fit a carry card; the chair should read it as "before costs").
- Where the number comes from (arithmetic on one ASSUMPTION): entry when the trailing-24 h
  funding F-bar is at least F* = 7 bp per 8 h (about 77% a year on notional), exit when it falls to
  F_exit = 2 bp. Assume the excess decays with a half-life of 5 days (15 settlements; UNSOURCED,
  measured at Gate 1). Collected funding = F* x sum over k of 0.5^(k/15) until F reaches 2 bp
  = 7 x 15.1 = 106 bp. Entry premium about 12 bp falling to about 7 bp at exit gives about +5 bp
  convergence.
- Sensitivity to the one assumption: half-life 2.5 days gives about 52 bp (1.5x cost, FAILS);
  5 days about 106 bp; 10 days about 213 bp. The card stands or falls on the tail half-life being
  at least about 4 days.
- Cost: spot taker 0.10% per side (Bybit VIP0) + 1 bp slippage = 22 bp round trip; perp 13 bp
  round trip; total C = 35 bp. Ratio 110 / 35 = 3.1 on the full two-leg cost (7-8x the perp leg's
  13 bp alone). WARNING: 1 bp slippage is a BTC-grade number. Thin tail alts may cost several
  times more per side, which would cut the ratio below 3. Book depth (from 2023-01) lets the
  statistician stress it.
- Where F* and F_exit come from (economics, not fitted): F* solves 3 x C = F* x L, where L is the
  decay-weighted number of settlements the position expects to stay above the exit level (about
  15 at the assumed half-life). F_exit is the funding at which the position stops beating the
  user's alternative: the 14.5% a year pre-tax hurdle is 1.32 bp per settlement on capital, and
  capital per unit notional is about 1.5 (spot 1 + perp margin 0.5 at 2x), so the break-even
  funding on notional is about 2.0 bp per 8 h. Below it the money is better in the ETF or in plain
  BTC/ETH carry (v0.18). The statistician fixes the grid around these two values.
- Price leg: hedged. The residual is the perp-minus-spot basis. Expected basis P&L is small and
  positive (convergence); the risk is a left tail when the perp spikes against the short (a
  squeeze) and the margin account, not the spot wallet, must fund it.
- Whole-portfolio honesty: if every number holds, about 30 episodes a year at 20% of equity each,
  about 75 bp net per trade, adds about 4-5% a year on equity, on top of whatever the idle
  capital earns in BTC/ETH carry (10-14% a year when invested). The portfolio lands near 12-15% a
  year, around the hurdle, not clearly above it. The card's claim is per trade, not that it
  clears 14-15%.

## Variables (all computable at the close of the decision bar t, UTC)

Data fields: Binance USDT-M `fundingRate` monthly archive (calc_time, funding_interval_hours,
last_funding_rate; verify column names), USDT-M klines (1 h or 5 m) for turnover ranking, Binance
spot klines for the hedge leg's price (proxy for Bybit spot), `premiumIndexKlines` (secondary),
`bookDepth` from 2023-01 (cost stress). Data status: funding and 5 m klines are held for 8 coins
only (HANDOFF section 6). **Funding for the other ~40-100 symbols, spot klines, premium-index
klines and depth are NOT held.** Whether delisted symbols are in the archive is unverified (the
bucket listing was not reachable from my tools); the data engineer must check.

- `f_s`: `last_funding_rate` printed at settlement s; `w_s`: funding interval in hours at s
  (from the file column, else from the spacing of calc_times).
- Per-8 h-equivalent rate `f8_s = f_s x (8 / w_s)`. Needed because some alts moved to 4 h or 1 h
  funding (Binance: to 1 h after a cap hit, effective 2025-05-02, back to 4 h after 16
  quiet cycles, effective 2026-01-02; Bybit switches to hourly at its limit).
- `F_bar_i,t` = mean of `f8_s` over settlements s of coin i with t - 24 h < s <= t.
  Reason for 24 h: three 8 h settlements smooth the 8 h premium window without lagging a multi-day
  episode. The statistician may test 48 h.
- Entry: `F_bar_i,t >= F*` and not already held. Exit: `F_bar_i,t <= F_exit`, or delisting, or
  loss of the spot market. No other filters in the primary. One position per coin.
- Sizing: equal notional across qualifying coins, at most K coins (K = 5 is the diversification
  scale: a single-name squeeze should cost no more than a fifth of the book), perp leverage at
  most 2x, spot unlevered. Idle capital: BTC/ETH carry (v0.18) in the labelled
  portfolio variant, cash in the primary.
- Trade P&L in bp of spot notional: sum of funding received on the short perp at the actual
  settlement rates (position value at the mark, proxy by the perp close at the settlement
  minute) + (spot return - perp return) - 35 bp. Entry fills at the open of the first minute bar
  after the decision close (not at the print), so the first accrual is at t + 8 h.
- **Sign trap for the builder.** Positive funding is RECEIVED by the short leg. A harness that
  treats funding as a cost for the position will flip the sign of the whole result. The engine
  needs a mutation test that flips the sign and fails.
- Margin check: simulate the short leg's liquidation price at 2x on 1-minute highs; report the
  share of trades that breach it and the extra capital needed to avoid it.
- Secondary (labelled "cannot rescue the primary"): trigger on the running premium-index estimate
  `P_hat` (H011 defines it) instead of trailing realised funding; the always-invested monthly
  top-k sort by trailing 30-day funding; the mirror for the negative tail (long perp, short spot
  via spot margin; borrow cost and availability make it weaker).

## Universe

Point-in-time, rebuilt on the first day of each month from data up to the prior day:
- Binance USDT-M perps (signal and funding source, deepest archive). Tradability is Bybit: require
  the coin also to have been listed on Bybit with a spot market for at least 90 days at t (Bybit
  listing dates must be derived from its own bulk archive; unverified that this exists).
- At least 90 days of history (first archive file as listing proxy; exchange APIs are blocked).
- Rank by trailing 30-day median daily quote turnover; primary = ranks 3-50 (BTC and ETH are the
  v0.18 object and rarely reach the tail; keep them as a control, no claim).
- Include coins that were later delisted. This matters more here than elsewhere: tail-funding
  episodes concentrate in manic coins, which are the ones most often delisted. A coin whose
  contract is delisted with a position open is closed at its last printed price and the loss is
  reported separately. If the archive lacks delisted symbols, say so and treat every positive
  result as an upper bound.
- Exclude stablecoin bases, index and dominance contracts, dated delivery contracts, TradFi and
  commodity perps, and any symbol with a multiplier change, rebrand or token migration inside the
  holding window (e.g. a 1000x-quoted perp needs its spot hedge quantity scaled).
- Capacity guard: entry notional at most 1% of the coin's trailing 24 h perp turnover (the
  statistician fixes it against depth). Expected strategy capacity is low hundreds of thousands
  of dollars; the user's size is far below it.

## Funnel estimate

Outcome-blind arithmetic from my prior, to be replaced by counts (a count of funding states
reveals no trade result): about 0.5-2% of alt coin-days in hot regimes and 0.1-0.5% in quiet ones
have F_bar at or above 7 bp. With about 45 coins, 100-250 coin-days a year, which de-cluster into
**about 20-40 episodes a year, 120-240 over 2020-09 to 2026-08**, concentrated in a handful of
euphoric months (perhaps 12-20 months of the 72). Quiet years (2022 H2, 2023) may have almost
none. The sample unit is the episode and the cluster is the month.

Power: the hedged trade's sd is basis noise plus squeeze events; assume 150-300 bp per trade. At
N = 150 independent episodes the minimum detectable mean is 2.8 x 150 / sqrt(150) = 34 bp (69 bp
at sd 300). The predicted net mean is 75 bp (110 - 35). **Feasible at the low-sd end, marginal at
the high-sd end**, and much better identified than any unhedged card because the funding cash
flow is nearly deterministic given the position.

Gate 1 data report (all funding-only, no trade P&L): (a) coverage of funding files for the PIT
universe including delisted symbols and the interval column; (b) the count of episodes at the
registered F*; (c) the measured half-life of F_bar in the tail state; (d) the share of
coin-days in the dead zone by year; (e) spot coverage and symbol mapping; (f) depth around tail
names for the cost stress. The half-life (c) is the one place this report touches the payoff's
main component. It is a persistence statistic of a public series, not a trade result, but the
chair should fix the grid in a committed pre-registration BEFORE any position is simulated.

## Falsifier

Drop the card if any of these hold:
1. Gate 1: the measured tail half-life is under about 3 days (collected funding then below about
   75 bp, under 2.1x cost), or fewer than about 60 independent episodes exist across the
   point-in-time universe including delisted names (untestable).
2. Verdict era (the freshest untouched block, by episodes not calendar time): mean funding
   collected per trade under 70 bp, or net mean (funding + basis - 35 bp) at or below zero, or the
   month-clustered t under the pre-registered bar.
3. Basis P&L is a fat left tail: mean basis P&L worse than about -50 bp per trade, or one or two
   months account for more than half of total P&L (a mania artifact, not a harvestable state).
4. Margin: at 2x perp leverage, more than about 10% of trades breach the liquidation price on
   1-minute highs. The capital ratio then exceeds 1.5 and the yield falls in proportion.
5. Cost stress: with slippage taken from the depth data on the tail names, the total round trip
   exceeds about 55 bp, which pushes the ratio under 2.
6. Decay: the freshest 12 months show a tail rate or half-life under half the earlier average
   (arbitrage capital arriving, as the ETF and the 11%-a-year gap-shrinkage findings suggest).

## Not claimed

- No claim about the direction of any price.
- No claim for BTC/ETH carry or for timing it (v0.18 settled that object).
- No claim about the funding-settlement flow (v0.24, 1-5 bp).
- No claim that the strategy clears the 14-15% a year hurdle at portfolio level; the arithmetic
  above says it lands around it.
- No claim that Binance funding equals Bybit funding. The signal is built on Binance's archive;
  the paid carry is Bybit's. If Bybit's bulk archive has premium-index data, compare the two on
  the tail coins before trusting the transfer.
- No claim about maker fills, and nothing here relies on a rebate.
- No claim of safety against exchange failure, delisting gaps or a depeg; none shows in a
  backtest.
- No claim about the negative-funding tail (secondary only), and none that unhedged versions
  (H002) are testable.
- Correlated-trial warning for the ledger: H001, H002 and H011 trade the same tail-funding
  states. If more than one is run, count them as correlated trials.
