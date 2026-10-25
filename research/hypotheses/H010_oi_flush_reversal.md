# H010: Post-flush reversal. Completed forced deleveraging is temporary price pressure

## Family and one-line claim

Family: forced-flow states on crypto perpetual futures (open interest, inferred liquidation).

Claim: after a coin's perpetual open interest has collapsed during a large price move, and the
collapse has stopped accelerating, the next 24 hours partly reverse that move. Trade against the
flush (long after a long-liquidation flush, short after a short-squeeze flush). This is a
REVERSAL claim, made for the liquid-alt tier. It is NOT made for BTC/ETH (see Not claimed).

## Mechanism

**1. Who is on the other side, and why do they lose?**
The losers are forced or panicked participants. Leveraged longs (or shorts) run out of margin and
the venue closes them at market whatever the price, then frightened holders close behind them.
Their flow is sized by margin, not by a view of value, so it is non-informational. The winner is
whoever takes the other side after the forced flow has stopped: a liquidity provider whose
capital is scarce exactly when the flow arrives.

**2. Why does it persist? (limit to arbitrage)**
- Risk capital of intermediaries is the scarce input and it withdraws in stress, which raises the
  reward for those who stay (Nagel 2012). A buyer also risks catching a still-falling price, so
  the premium is the pay for that risk, and it is only collectable once forced flow has ended
  (Brunnermeier and Pedersen 2009, liquidity spirals).
- Capacity: a few tens of thousands of dollars per coin per event before the trade moves the
  price. That is too small for funds to bother with (inconvenience, not "nobody noticed").
- Unsourced conjecture: HFT market makers compete the premium away within minutes, so only the
  slower part (hours) is left for a taker who enters after a completed flush.

**3. Sources, and what each one actually measured**
(All read at abstract, summary or table level through web fetches, not in full.)
- Coval and Stafford (2007), *Asset fire sales (and purchases) in equity markets*, JFE 86(2).
  Mutual-fund trades forced by investor flows depress prices and later reverse, and liquidity
  providers earn large returns. Scale: equities, months to quarters (fire-sale stocks fell about
  10% and recovered about 7.7% over months t+4 to t+12). It says nothing about hours or crypto.
- Nagel (2012), *Evaporating liquidity*, RFS. Short-term reversal returns are predictable by VIX
  and highest when liquidity suppliers pull back. Equities, not crypto.
- Brunnermeier and Pedersen (2009), *Market liquidity and funding liquidity*, RFS 22(6). Theory:
  margin calls and loss spirals. Not read in full here.
- Llorente, Michaely, Saar, Wang (2002), *Dynamic volume-return relation of individual stocks*,
  RFS 15(4). Returns from risk-sharing (non-informational) trades tend to reverse and returns
  from speculative trades tend to continue. Used only as the principle that the TYPE of flow
  decides the sign. The abstract does not state the direction by volume level; not used for more.
- Zaremba, Bilgin, Long, Mercik, Szczygielski (2021), *Up or down? Short-term reversal, momentum,
  and liquidity effects in cryptocurrency markets*, International Review of Financial Analysis
  78. Over 3,600 coins, previous-day losers beat winners, and the authors tie this to
  illiquidity. Among the largest and most tradeable coins the sign flips to daily momentum.
  This is why the claim is made for liquid alts and not for BTC/ETH. Caveat: their coins are
  mostly spot micro-caps with no perp, so the transfer to the top-40 perps is partial. It also
  warns that the reversal may live only in coins where real spreads exceed the 13 bp cost.
- Osler (2005), *Stop-loss orders and price cascades in currency markets*, JIMF (NY Fed Staff
  Report 150). After rates reach round-number stop clusters, trend continuation is significant
  for at least 2 hours, take-profit reversal lasts under 30 minutes, and results are
  "statistically significant for hours, although not for days". Cascades are inferred
  indirectly, and at round numbers (a location).
  HONEST TRANSFER CHECK: Osler does NOT support a 4-72 h continuation claim, and she does NOT
  say what follows a completed flush. What it does give is the failure mode of this card:
  entering while the cascade is still running. That is why a completion condition is part of the
  state. If a perp flush leaves hours of continuation, a 24 h hold will net it out against the
  reversal, and that is the main risk to this hypothesis.
- Preprints only, single author, not peer-reviewed, abstract-level reading: Garcia Seuma (arXiv
  2607.27070 and 2608.03616, 2026) on seven BTC cascades says most forced selling happens
  quickly and much is absorbed off-book by the venue backstop; open interest falls and price
  impact spikes inside the cascade. Consistent with "the forced flow is over by a 1 h bar", not
  verified. Cheng, Deng, Wang, Yu (arXiv 2102.04591, 2021): BitMEX, 2020-21 sample, average daily
  forced liquidations were 3.51% of OI for longs and 1.89% for shorts, and liquidated accounts
  averaged about 60x leverage. Used only as a SCALE for what "normal" forced closing is.
- Data-validity warning: Giagkiozis and Said (*Ledger* 2024) report that on several exchanges,
  Binance among them in one 2023 window, open-interest changes exceed traded volume, so OI can
  be misreported or delayed. Every OI-based state here inherits that noise.

**Inference assumption, flagged.** There is no liquidation feed for BTCUSDT (EDGE_LAB section 4).
"Forced flow" is therefore INFERRED. Open interest is symmetric (every long has a short), so OI
alone never says which side was closed: the sign comes from price direction. A falling OI also
contains voluntary closing. The taker-flow footprint is the only extra evidence: liquidation
orders are market orders, so a long flush should show taker selling dominance. This inference
is the weakest link in the card.

**State, not location (Q3).** No price level is drawn. The state is "leverage was removed
quickly, and the removal has ended".

## Prediction

- Sign: against the flush move. Long after (R very negative and OI collapsed), short after
  (R very positive and OI collapsed).
- Horizon: h = 24 bars of 1 h (decision on the 1 h close; entry at the first tradable price
  after the close; exit at the close of the bar 24 h later). Real funding is charged by the
  harness; the hold spans three settlements.
- Expected gross excess per trade (vs the drift-matched unconditional 24 h return of the same
  coin): **+100 bp** in the liquid-alt tier. BTC/ETH: not claimed (assume 0, possibly negative).
- Where the number comes from (an ASSUMPTION, not a measurement): qualifying flush moves are
  at least 5% by construction (the cost floor below) and are typically 10-15% in alts; I assume
  7-10% of the move reverses in the next 24 h. Coval and Stafford saw roughly three quarters of
  a 10% fire-sale drop reverse over months 4 to 12 after the event, so a 7-10% share within a
  day is a deliberately small fraction of that, but no source gives a day-scale share for crypto.
- Cost ratio: 100 / 13 = 7.7 on the 13 bp assumption. WARNING: 13 bp is a BTC-grade number.
  Alt spreads and slippage right after a flush are several times wider, so the statistician
  should run a cost schedule by liquidity tier before believing the ratio.

## Variables (all computable at the close of the decision bar t, UTC)

Data fields: 5 m perp klines (open, high, low, close, volume, taker_buy_base_volume);
Binance USDT-M daily `metrics` files (`sum_open_interest` in base-asset units, 5 m).
Data status: 5 m klines are held for BTC, ETH, BNB, XRP, ADA, DOGE, SOL, LINK only (HANDOFF
section 6). **The metrics (OI) files and the rest of the universe are NOT yet held.** Whether
delisted symbols are still in the archive must be checked by the data engineer.

- `P_t`: close of the 1 h bar ending at t (perp last-price klines).
- `OI_t`: `sum_open_interest` from the latest metrics row stamped at or before t minus 5 minutes.
  Use coin units, not USD value, because USD OI changes mechanically with price. The stamp
  convention (start or end of the 5 m snapshot) must be verified; the 5 m lag is a safety margin.
- `W` = 24 h. Reason for the scale: forced flow finishes within minutes to hours, but the
  voluntary close-out that follows takes up to a day, and the card needs both finished.
- `dOI_t = ln(OI_t / OI_{t-W})`, `R_t = ln(P_t / P_{t-W})`.
- `sigma_i`: standard deviation of 1 h log returns over the 30 days ending at t-W, scaled by
  sqrt(24). It ends before the window so the flush cannot inflate its own yardstick.
- Flush size: `|R_t| >= max(k * sigma_i, 5%)`. The 5% floor is a cost-derived number, not a
  fitted one: a 40 bp edge needs a move of at least 40 bp / 8% = 5% if about 8% of it reverses.
  The statistician fixes k.
- OI-loss tail: `dOI_t` ranks in the lowest fraction q of that coin's own history of 24 h OI
  changes up to t-W (point-in-time, expanding). Reason for the scale: normal forced closing is
  about 2-4% of OI a day (Cheng et al., preprint), so an extreme tail is several times normal.
  q is sized so that the OI condition alone gives about 4 coin-days per coin-year, which is a
  funnel design target, not a value read off outcomes. The statistician fixes q.
- Completion: `ln(OI_t / OI_{t-2h}) >= (2/W) * dOI_t`. Both sides are negative; the condition
  says the last two hours lost OI no faster than the window's average pace.
- Optional confirmation (secondary, not in the primary): taker imbalance over the window
  `(2 * taker_buy_base_volume - volume) / volume`, summed over the window; a long flush should be
  in the taker-selling tail.
- Direction `d = -sign(R_t)`.
- One entry per coin per 24 h (cooling period).

## Universe

Binance USDT-M perpetuals, rebuilt at each decision time from information up to t only:
- Listing date from the first archive file for the symbol; require at least 90 days of
  history (needed for the expanding OI tail and sigma).
- Tier A: ranks 3-40 by trailing 30-day median daily USDT turnover as of t-1 day (primary).
  Tier B: BTCUSDT and ETHUSDT (control, no claim). Tier C: ranks 41-120 (secondary; the
  reversal is likelier here but real costs are worse).
- Include symbols that were later delisted or collapsed, otherwise the reversal is
  survivorship-biased in exactly the way that matters (a coin in a death spiral does not
  bounce). If the archive lacks delisted symbols, say so in the data report and treat any
  positive result as an upper bound.
- Exclude index and dominance contracts, delivery (dated) contracts, and any symbol with a
  contract multiplier change inside the window.

## Funnel estimate

Outcome-blind arithmetic, to be confirmed by the data engineer with counts (counts reveal no
P&L): an OI tail sized at about 4 coin-days per coin-year, cut by the price condition (flush
and a big move usually co-occur, so perhaps half survive) and by the completion condition (about
half again), gives roughly 1-2 entries per coin-year. With about 40 liquid coins that is
**40-80 entries a year, 240-480 over 2020-09 to 2026-08.** Events are market-clustered: one
crash day produces many coin entries, so date-clustered independent events are about 15-30 a
year, 90-180 in total.

Power (assumptions, not data): trade sd at 24 h in flush states about 800 bp for alts. The
minimum detectable effect (alpha 0.05 two-sided, power 80%) is about 2.8 * 800 / sqrt(N):
112 bp at N = 400, 79 bp at N = 800. **The central prediction (100 bp) sits at the edge of
what the full-history sample can resolve**, so a verdict era holding only the last year will
not resolve it. The statistician should say so and may prefer the beta-residual return (alt
minus beta times BTC) as the measured quantity to cut the sd, with the hedge leg's extra cost
shown separately. BTC/ETH alone: about 2 qualifying events a year each, on the same days, so
**fewer than 20 independent events in total. It can never be tested on its own.**

## Falsifier

Drop the card if any of these hold:
1. Tier A signed 24 h excess (measured from the first tradable price after the decision bar) is
   at or below 13 bp on the freshest untouched year-block, or its sign differs across two or more
   of three equal era blocks.
2. No dose-response: the excess does not grow from a moderate to an extreme OI-loss tail. A
   reversal that appears at one (k, q) cell only is an island, not a mechanism.
3. Placebo: coin-days with the same large |R| but OI NOT collapsed (the H012 comparison group)
   revert just as much. Then the reversal is ordinary illiquidity reversal (Zaremba et al.),
   not forced flow, and this card's mechanism is wrong even if a reversal exists.
4. The reversal is complete within the first one to two hours after the decision bar, so the
   price at the first tradable fill has already recovered (the CLAUDE.md "right about the
   reaction, not an edge" trap).
5. The effect exists only in symbols later delisted or missing from the archive, or only
   where the realistic spread exceeds the 13 bp assumption.

## Not claimed

- No claim for BTC/ETH. Zaremba et al. point to momentum in the largest coins.
- No claim about a cascade that is still in progress (OI still falling at the decision bar).
  That state is excluded by the completion condition, not predicted.
- No claim about market-wide information shocks (insolvency news, depegs). Those are flushes
  with a fundamental cause and may continue; the pooled test will show this as a fat left
  tail. Splitting by BTC's own OI collapse is a secondary.
- No claim about what causes the OI loss (liquidation versus voluntary closing); only that the
  flow type matters for the sign.
- No claim at horizons under 4 h or over 72 h.
- Not the funding-settlement effect (v0.24) and not a location effect.
