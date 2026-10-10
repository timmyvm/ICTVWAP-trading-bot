# Strategy catalogue: learn what published strategies rely on

Owner: the chair (main session). Cards in `research/catalogue/`. Started v0.36.

## 1. Why this exists

The edge lab (docs/EDGE_LAB.md) asks a confirmation question: "is this one pre-registered idea
real?" Confirmation needs a lot of independent events, and a retail edge below ~150-300 bp per
independent event cannot be told from zero on ~6 years of data. That is the wall the first 34
strategies hit.

This catalogue asks an **exploration** question instead: "what does each published strategy rely
on, who is on the other side, and in what state of the market does that hold?" Exploration has
no significance bar, because its output is a hypothesis, not a claim. The only rule is that
exploration output is never used as proof of itself (section 5).

The working belief, to be checked rather than assumed: 100-200 published strategies are
8-10 **primitives** wrapped in different entries, stops and targets. The wrapper is where P&L is
lost (docs/failure_path.md: location is not information; stop below the cost floor). The
primitive can be measured with no wrapper, on millions of bars across hundreds of coins, which
is far more data than a strategy's few dozen trades. Breadth (many assets, many horizons) is how
shops with the same calendar as us get power; we use the 700-symbol archive for it.

## 2. The primitives (fixed list; scouts tag every card with these)

| id | primitive | one-line definition | measured later as |
|---|---|---|---|
| P1 | serial dependence | past signed return/z-score over h predicts the next h' (trend vs reversal) | forward return after the state, by horizon, minus drift |
| P2 | volatility state | range/vol clusters; predicts the SIZE of the next move, not its sign | forward abs return or range after the state |
| P3 | cross-sectional relative strength | an asset's rank among peers (after beta) predicts its relative return | dollar-neutral quantile spread, full-turnover cost |
| P4 | carry | being paid for holding a position (funding, basis, roll, premium) | realised carry minus the adverse price move |
| P5 | calendar and clock flow | hour, session, weekday, month, scheduled events | mean return by clock bucket, de-meaned, date-clustered |
| P6 | positioning and leverage state | open interest, liquidations, long/short, funding extremes | forward return after the extreme state |
| P7 | liquidity and volume state | volume spikes, VWAP distance, profile, depth | forward return / vol after the state |
| P8 | price-location reaction | levels, zones, gaps, patterns, fibs (the retail default; prior ~ 0) | forward return after a touch vs matched non-touch |
| P9 | other / composite | name the new primitive in the card | defined when proposed |
| P10 | resting-order clustering | stop and take-profit orders cluster at round numbers and recent extremes, so price behaves differently on passing through them (Osler 2000, 2003) | forward return and range after trading through a round number or a recent extreme, vs matched non-touch |

P10 was added by the chair after phase 0 (section 7). P1 is split by holding horizon when phase 1
re-tags the cards: P1a intraday (up to 1 day), P1b days to weeks, P1c months. A trend rule and a
reversal rule are the same primitive at opposite signs, and which one holds depends on the horizon
band, so one P1 bucket hides the thing we most want to learn.

A card may carry one primary and up to two secondary tags. If a strategy needs a 10th primitive,
the scout names it; the chair decides whether it joins the list.

## 3. A catalogue card

Cards are markdown, one per strategy, in `research/catalogue/<family>.md` (a family file holds
many cards). Every card has these fields and nothing in it may be a backtest result:

- **Id and name.** `S-<FAM>-NN`.
- **Fidelity.** A = primary source gives exact rules; B = a secondary source describes them;
  C = folklore (no primary source found). Never invent a source. A rule that cannot be written
  as a mechanical rule is graded C and marked "not mechanizable".
- **Sources.** Title, author, year, URL. Say whether you read the whole page or only an abstract.
- **Rule.** Signal, direction, entry, exit or holding horizon, universe and timeframe, data needed.
  Written so that two engineers would build the same thing.
- **Primitive vs wrapper.** Primary and secondary primitive tags; then which parts of the rule are
  wrapper (stop, target, confirmation candle, session gate, filter).
- **Claimed mechanism.** Who is on the other side and why they lose or accept it; why it persists
  (limit to arbitrage). "Nobody noticed" is not an answer; say so if that is all the source offers.
- **Published claim.** What the source reports, with market and era, labelled as the source's
  number, not ours.
- **Decay and crowding.** Any evidence the effect shrank after publication or in later samples.
- **Cost-floor note.** Typical move over the holding horizon vs the 13 bp round trip, as
  arithmetic from the rule, not from data.
- **Event rate (estimate).** Rough number of date-independent events per year, labelled estimate.
- **Applies to / testable here.** Markets the source covers (crypto perps, equities, FX, futures)
  and whether our data can test it: Y (Binance/Bybit archive klines 1m-1d, funding, open interest,
  long/short and taker flow for ~700 USDT perps), partial (needs a feed we only have for a few
  markets, e.g. cached NQ/FX/gold intraday or Yahoo daily), or N (names the missing data).
- **Regime hypothesis.** When the mechanism says it should work and when it should fail. Stated
  now, before any data, so it can be checked later.
- **Overlaps.** Other cards that are the same primitive with a different wrapper.

## 4. Phases

| phase | what | trials spent |
|---|---|---|
| 0 | scouts compile cards per family (this document's cards); chair checks sources and consolidates an index and a primitive map | 0 |
| 1 | outcome-blind triage: event rate and funnel counts per primitive on the explore data; drop cards that duplicate another's primitive | 0 |
| 2 | primitive probes: one pre-registered probe per primitive x horizon grid x regime split on the EXPLORE data. Each grid cell is logged with `ledger.log_exploration` | counted |
| 3 | combination search on EXPLORE data only: state variables that say when a primitive holds, pairs of primitives; every candidate counted | counted |
| 4 | the best few combinations go to the SEALED data once each (`open_holdout`), then to the forward paper tracker at small size | one per combination |

Phases 2 and 3 are exploration; reading their results never counts as a pass.

## 5. The data split (set before the first probe, recorded in the ledger)

- **Explore set.** The early part of history and coin half A. Anything may be tried here, as often
  as we like; every cell is logged and counts as a trial.
- **Sealed set.** The freshest period (at least 18 months) and coin half B, split by a fixed rule
  (symbol-name hash parity) decided before any probe is run. Not read in phases 0-3. Each
  combination that reaches phase 4 opens it once.
- The exact dates and the coin rule are written into the first phase-2 pre-registration, before any
  result exists.
- Why both: era alone leaves room for era luck; coin split alone leaves market-wide luck.
  A combination that holds on the unseen era AND the unseen coins has had two chances to fail.

## 6. Success and failure

Success is not "a profitable strategy was found". Success is: (a) a primitive map saying which
primitives are present, in which regimes, at what size relative to cost, and (b) at least one
combination whose reason is stated in advance, taken to the sealed set once. Most primitives will
be absent or sub-cost; that is a finding. A combination that fails the sealed set is a finding
too and is written into HANDOFF as such.

## 7. Phase 0 result (2026-10-10) and the chair's decisions

Nine scouts wrote 144 cards (16 per family) into `research/catalogue/`; `INDEX.md` is generated by
`build_index.py`. No data was opened, no trial was spent. Facts below are what the scouts report from
the published sources; the chair re-read three of the key sources against the originals (one
mislabelled section reference was fixed). 53 of the 144 cards contain at least one claim taken from
memory and not re-fetched; those are marked on the card and counted in the index.

- **Coverage.** Fidelity A / B / C = 64 / 52 / 28 (INDEX.md has the live counts). Testable on our
  data: Y 86, partial 33, N 25 (the scouts' own judgement).
- **The primitive map is lopsided.** 55 of 144 cards are P1, 17 are P5, 16 each are P4 and P8.
  P1 lumps trend and reversal together, which is why phase 1 splits it by horizon band (section 2).
- **Decisions on the scouts' proposals.** Accept P10 (resting-order clustering). Keep the P9
  sub-labels (lottery, news, valuation, signed order flow, capital flow, attention) as sub-tags,
  not new primitives, until a probe needs them.
- **What the sources say about size versus cost** (their numbers, not ours): several published
  effects are smaller than a 13 bp round trip as published, for example the crypto hour-of-day
  effect (about 9-11 bp gross) and 15-minute crypto reversal (about 1.3 bp gross, which the paper
  itself says does not cover costs). Funding carry has compressed in the latest sample. None of the
  ML papers read uses purged validation. These shape phase 1; they are leads, not conclusions.

## 8. Rules carried over

- Costs: 13 bp round trip (taker 0.055% + 0.01% slippage a side), real funding, spot 0.10% a side.
  Adverse selection is deliberately not modelled yet; maker variants are labelled secondary.
- No lookahead: higher-timeframe bars mapped by CLOSE time, truncation guard on every signal.
- Never "drop the losers and rerun" or "combine the best parts" by P&L. Combination happens at
  primitive level with a stated reason, on EXPLORE data, and is counted.
- Every code or config change gets a DEVLOG entry; every mistake gets a CLAUDE.md lesson.
