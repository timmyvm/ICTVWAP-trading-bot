# P2 power table: tiers, grid, power, sealed-open rules, regimes

Statistician's draft for the chair, 2026-10-11. Companion to `P2_primitive_probes.md`.
Nothing here is a result. Every number is either a count, a coverage figure, an unconditional
moment of the explore quadrant, or an assumption that is labelled as one.

## 0. What was read and what was computed

Read: `docs/CATALOGUE.md`, `docs/EDGE_LAB.md`, `docs/HANDOFF.md` section 3,
`research/catalogue/PROBE_LIBRARY.md`, `research/catalogue/probes/*.json` (all 201 real probes, record
by record), `backtest/edge_lab/{power,ledger,measure,split}.py`, `research/prereg/split_assignment.csv`,
`research/data_reports/H001_carry_data.md` and `H010_flow_data.md`.

Computed, on the EXPLORE quadrant only (the 191 half-A symbols with explore days; 1d bars stamped on or
before 2024-12-31; funding settlements of half-A symbols up to 2024-12-31 23:59 UTC):

- coverage: coin-days, names per day, history ages, missing calendar days;
- unconditional standard deviation of h-day open-to-open returns (h = 1, 7, 30), the convention of
  `measure.trade_return` (decide at the close of t, enter at the open of t+1, exit at the open of t+1+h),
  zero-volume days treated as not live;
- the same-date intra-class correlation of those returns (one-way ANOVA estimator over dates);
- the sd of an equal-weight index, of |r|, and of a placebo long-short spread whose sort key is a hash
  of (symbol, date), which carries no information;
- the correlation of the equal-weight indices of two hash-chosen sub-halves of half A;
- the distribution of each proposed regime variable (days per level; no returns);
- the funding-interval mix of half-A settlements.

Not computed: any return conditional on a signal, state or regime; any P&L; anything from late_A, early_B
or late_B other than the counts in `split_assignment.csv`. BTCUSDT was not opened (it is in half B).
The computations were run from a session scratch directory and are not committed; section 4.1 gives
enough detail to reproduce every input.

## 1. Five findings that change the design

1. **BTCUSDT is in half B.** No BTC-based regime variable, market hedge or universe member may be
   read in phases 2-3. The market proxy everywhere (explore and sealed) is MKT_A10, the equal-weight
   index of the 10 most liquid half-A coins (section 6). Note also that `universe_pit.csv` ranks are
   computed across both halves; phase 2 must rank within half A.
2. **For market-exposed statistics, early_B is not a holdout.** Same-date correlation of coin returns
   is 0.48 / 0.44 / 0.39 at 1 / 7 / 30 days, so about 98 % of the variance of a pooled 44-coin window
   mean is the common market move. Two random sub-halves of half A have equal-weight index correlation
   0.94 / 0.94 / 0.95. Half B on the same dates will be about as close. A directional result found on
   explore will therefore "replicate" on early_B whether it is real or not. For directional and
   market-wide statistics the only fresh data are the 638 dates of 2025-01-01 to 2026-09-30.
3. **Directional (unhedged) primitives cannot be confirmed with this sealed set.** Over the 1.75-year
   late era a t-bar of 2.58 at 80 % power resolves only an annual Sharpe of about 2.6 (2.2 at t = 2);
   a Sharpe of 1.0 needs 11.7 years (`power.years_for_sharpe`). What the sealed set can confirm is
   market-neutral: cross-sectional spreads, pairs and market-hedged time-series alpha at 1-3 day holds,
   and 7-14 day holds only for large effects. Holds of 20 days or more, and every monthly-decision cell,
   are descriptive only.
4. **Data defects to fix before the first probe.** (a) 2022-02-26..28 is missing from the 1d files of
   21 of the 67 half-A coins that span that date (the truncated monthly zips engineer B suspected);
   186 calendar days are missing inside half-A explore spans in all (TLMUSDT 29, ICPUSDT 26, BNXUSDT 26).
   Patch from the daily archive. (b) 54 of 191 half-A symbols have no funding file (the H001 fetch
   covered only coins ever in the overall top 60); on a typical day 34-39 of the 50 U50A coins have
   funding. Fetch funding for every half-A coin that ever enters U50A. (c) 19.0 % of half-A explore
   settlements (45 coins, 2023-24) are on 4 h or 1 h intervals: funding paid must be the sum of `rate`,
   never of `f8`, or those coins are charged 2-8 times their real funding.
5. **The T1 grid is 304 cells.** By what the sealed set could ever resolve: 92 resolvable in
   market-neutral form, 83 only for large effects, 129 descriptive only (section 4.5).

## 2. Task A: tiers at probe level

Definitions used:

- **T1**: computable from what is held locally: USDT-M 1d klines (`klines_1d_um/`, 712 symbols:
  open, high, low, close, volume, quote_volume, trades) and/or settled funding (`funding/`).
- **T2**: needs a download or an external series: 1 h-12 h klines; open interest, long/short or taker
  metrics; taker columns of klines (the held 1d files do not carry them); spot, index, premium,
  dated-futures or coin-margined klines; a public event calendar; an external daily series (Yahoo,
  CFTC). Downloaded for half A only until the sealed open.
- **T3**: 15 m bars or finer, or tick. Out of scope for this pre-registration.
- **P**: parked. Needs data we cannot get (options, FX forwards, equity-only series with no crypto
  analog, market cap, on-chain, order book, liquidations, vendor indices), or the mechanism does not
  exist in a 24/7 market (session gaps, cash opens).

A probe is tiered by the bar and data its card publishes. A card that says "any timeframe" keeps the bar
the scout recorded. A 1d variant of a multi-frequency study is T1.

| archetype | T1 | T2 | T3 | P | total |
|---|---|---|---|---|---|
| CARRY | 0 | 4 | 0 | 11 | 15 |
| CLOCK | 4 | 3 | 1 | 2 | 10 |
| EVENT | 0 | 6 | 0 | 2 | 8 |
| FLOW_STATE | 1 | 10 | 0 | 7 | 18 |
| LEVEL_TOUCH | 8 | 1 | 10 | 0 | 19 |
| MODEL | 7 | 0 | 0 | 4 | 11 |
| TS_STATE | 48 | 2 | 6 | 10 | 66 |
| VOL_STATE | 13 | 0 | 1 | 0 | 14 |
| XS_RANK | 21 | 1 | 3 | 15 | 40 |
| **total** | **102** | **27** | **21** | **51** | **201** |

Of the 102 T1 probes: 73 feed grid cells, 13 collapse onto another card's cells, 5 lack a published
non-hold parameter ("unspecified", back to the chair), 8 are composite models deferred to phase 3, and
3 are infeasible (fewer than 12 independent explore windows).

Calls the chair should see:

- **S-FLOW-01a** (taker imbalance, 1d) is T2: the held 1d files dropped the taker columns. A 1d
  re-download for half A is small.
- **S-CARRY-04a** is parked: Bybit has no funding archive (H001 report section 7), so the card's
  "both series are in the archive" is wrong.
- **S-CARRY-05a** (cross-sectional funding) is T1 but needs defect 4(b) fixed first.
- **EVENT probes** are T2, not T1: each calendar must be built and checked against the market's
  release-minute spike (the repo's lesson on scraped event calendars). S-CAL-14c's published target is BTC; in
  explore it must be ETH or MKT_A10.
- **MODEL composites** (deep momentum network, deep RL, GP-evolved rules, HMM, jump model, ML
  ensemble) are deferred: their inputs are P1/P2 states the grid measures directly, and the GP card
  alone would add thousands of trials. The HMM and jump-model cards publish a 3000-day fit window;
  the explore quadrant has 1,827 days.
- **Collapses** that look like losses but are not: S-BRK-10a (4,536 variants published only as
  ranges), S-BRK-11a, S-TREND-07c and S-BRK-10b publish no lookback values; all are the Donchian state
  and fall onto TS-F's published lookbacks.

Full probe-level table (status: grid family, collapsed, unspecified, deferred, infeasible):

| probe | archetype | variable | bar | tier | phase-2 status | note |
|---|---|---|---|---|---|---|
| S-CARRY-14b | CARRY | atm_call_premium | 1d | P | - | SPX options |
| S-CARRY-14a | CARRY | atm_put_premium | 1d | P | - | SPX options |
| S-CARRY-15b | CARRY | atm_straddle_premium | 1d | P | - | index options |
| S-CARRY-10a | CARRY | average_forward_discount | 1mo | P | - | FX forwards |
| S-CARRY-12b | CARRY | basis | 1mo | P | - | equity index futures |
| S-CARRY-09a | CARRY | forward_discount | 1mo | P | - | FX forwards |
| S-CARRY-04a | CARRY | funding_spread | 8h | P | - | no Bybit funding archive (H001 report s.7) |
| S-CARRY-16a | CARRY | otm_call_premium | 1h | P | - | Deribit IV history |
| S-BRK-15a | CARRY | variance_risk_premium | 1d | P | - | option prices |
| S-CARRY-15a | CARRY | variance_risk_premium | 1d | P | - | option strips |
| S-CARRY-16b | CARRY | variance_risk_premium | 1d | P | - | Deribit IV history |
| S-CARRY-02a | CARRY | basis | 1h | T2 | - | spot + premium 1h; Aave leg set to 0 as a labelled adaptation |
| S-CARRY-03a | CARRY | basis | 1d | T2 | - | dated-futures + spot 1d; ETH only in half A |
| S-CARRY-01a | CARRY | funding_rate | 8h | T2 | - | spot (or index-price) klines for the hedge leg |
| S-CARRY-04b | CARRY | funding_spread | 8h | T2 | - | coin-margined funding + klines |
| S-CAL-07a | CLOCK | trading_session | 1h | P | - | FX only; no crypto session times published |
| S-CAL-04b | CLOCK | turn_of_year | 1d | P | - | equity index, no crypto analog on card |
| S-CAL-01a | CLOCK | day_of_month | 1d | T1 | grid C-A | UTC month boundary |
| S-CAL-05a | CLOCK | month_of_year | 1mo | T1 | infeasible | 4 explore seasons |
| S-CAL-04a | CLOCK | turn_of_year | 1d | T1 | infeasible | 4 explore Januaries; size proxied by turnover |
| S-CAL-02a | CLOCK | weekday | 1d | T1 | grid C-B | weekend vs weekday UTC |
| S-BRK-07a | CLOCK | hour_of_day | 1h | T2 | - | 1h; published UTC windows applied to perps |
| S-CAL-08a | CLOCK | hour_of_day | 1h | T2 | - | 1h |
| S-PAT-15a | CLOCK | hour_of_day | 1h | T2 | - | 1h, New York DST mapping |
| S-CAL-06b | CLOCK | trading_session | 15m | T3 | - | session boundary at :30 UTC |
| S-CAL-14a | EVENT | equity_weight_drift | 1d | P | - | equity and bond futures |
| S-CAL-13a | EVENT | index_membership_change | 1d | P | - | S&P 500 change list |
| S-CAL-14c | EVENT | equity_weight_drift | 1d | T2 | - | SPX + 10y daily (Yahoo); target ETH/MKT_A10 not BTC |
| S-CAL-10b | EVENT | fomc_cycle_week | 1d | T2 | - | FOMC calendar |
| S-CAL-11a | EVENT | macro_announcement_day | 1d | T2 | - | macro release calendar |
| S-CAL-15a | EVENT | option_expiration_week | 1d | T2 | - | expiry calendar (Deribit, recalled) |
| S-CAL-10a | EVENT | pre_fomc_window | 15m | T2 | - | 1h + FOMC calendar (14:00-14:00 ET variant) |
| S-CAL-03a | EVENT | pre_holiday | 1d | T2 | - | NYSE holiday calendar |
| S-CARRY-03b | FLOW_STATE | basis | 1d | P | - | liquidations |
| S-FLOW-14b | FLOW_STATE | exchange_net_inflow | 1h | P | - | labelled exchange flows |
| S-FLOW-14c | FLOW_STATE | exchange_net_inflow | 1h | P | - | labelled exchange flows |
| S-FLOW-02b | FLOW_STATE | order_flow_imbalance | tick | P | - | L1 quotes |
| S-FLOW-02a | FLOW_STATE | queue_imbalance | tick | P | - | L1 queues |
| S-FLOW-14a | FLOW_STATE | stablecoin_issuance | 1h | P | - | on-chain issuance |
| S-FLOW-01b | FLOW_STATE | taker_imbalance | tick | P | - | signed trade counts |
| S-FLOW-10b | FLOW_STATE | funding_rate | 8h | T1 | grid F-A | runs only if funnel shows >= 12 windows |
| S-FLOW-10a | FLOW_STATE | basis | 1d | T2 | - | dated-futures basis; ETH only in half A |
| S-FLOW-11a | FLOW_STATE | cot_sentiment_index | 1w | T2 | - | CFTC COT (public; reachability unverified); ETH only in half A |
| S-FLOW-11b | FLOW_STATE | cot_sentiment_index | 1w | T2 | - | CFTC COT (public; reachability unverified); ETH only in half A |
| S-CARRY-06a | FLOW_STATE | funding_rate | 8h | T2 | - | 8h hold needs 8h klines |
| S-FLOW-09a | FLOW_STATE | long_short_ratio | 1d | T2 | - | long/short ratio (metrics) |
| S-FLOW-08a | FLOW_STATE | oi_price_quadrant | 1d | T2 | - | open interest |
| S-FLOW-08b | FLOW_STATE | oi_price_quadrant | 1d | T2 | - | open interest |
| S-FLOW-07a | FLOW_STATE | open_interest_change | 1mo | T2 | - | open interest; sector map |
| S-FLOW-08c | FLOW_STATE | open_interest_change | 1h | T2 | - | open interest, 1h |
| S-FLOW-01a | FLOW_STATE | taker_imbalance | 1d | T2 | - | taker-buy columns (held 1d files dropped them) |
| S-PAT-01a | LEVEL_TOUCH | candle_pattern | 1d | T1 | grid L-A |  |
| S-PAT-01b | LEVEL_TOUCH | candle_pattern | 1d | T1 | grid L-B |  |
| S-PAT-02a | LEVEL_TOUCH | chart_pattern | 1d | T1 | grid L-C |  |
| S-PAT-02b | LEVEL_TOUCH | chart_pattern | 1d | T1 | grid L-D |  |
| S-PAT-06a | LEVEL_TOUCH | fib_retracement_cross | 1d | T1 | unspecified | swing window |
| S-PAT-06b | LEVEL_TOUCH | fib_zone_touch | 1d | T1 | unspecified | swing rule |
| S-BRK-02c | LEVEL_TOUCH | setup_bar_extreme_break | 1d | T1 | grid L-E |  |
| S-BRK-10b | LEVEL_TOUCH | support_resistance_break | 1d | T1 | collapsed onto TS-F | j unpublished; = Donchian |
| S-PAT-07a | LEVEL_TOUCH | harmonic_pattern | 1h | T2 | - | 1h |
| S-PAT-14a | LEVEL_TOUCH | fvg_zone_touch | 1m | T3 | - | 1m |
| S-PAT-05b | LEVEL_TOUCH | pivot_level_break | 1m | T3 | - | 1m |
| S-PAT-05a | LEVEL_TOUCH | pivot_level_touch | 1m | T3 | - | 1m |
| S-PAT-03b | LEVEL_TOUCH | prior_extreme_touch | 1m | T3 | - | 1m |
| S-PAT-04b | LEVEL_TOUCH | round_number_cross | 1m | T3 | - | 1m |
| S-FLOW-06a | LEVEL_TOUCH | round_number_touch | 1m | T3 | - | 1m |
| S-FLOW-06b | LEVEL_TOUCH | round_number_touch | 1m | T3 | - | 1m |
| S-PAT-04a | LEVEL_TOUCH | round_number_touch | 1m | T3 | - | 1m |
| S-PAT-14b | LEVEL_TOUCH | swing_break | 1m | T3 | - | 1m |
| S-PAT-12a | LEVEL_TOUCH | value_area_reentry | 1m | T3 | - | 1m; 24/7 session invented |
| S-MOD-09a | MODEL | btc_direction_classifier | 1m | P | - | on-chain, tweet, cross-asset minute features |
| S-MOD-10a | MODEL | characteristics_return_forecast | 1d | P | - | accounting characteristics |
| S-MR-13b | MODEL | residual_s_score | 1d | P | - | sector ETFs |
| S-MR-13c | MODEL | residual_s_score | 1d | P | - | sector-ETF factor |
| S-MOD-06a | MODEL | deep_momentum_network | 1d | T1 | deferred (composite) | composite model |
| S-MOD-11a | MODEL | deep_rl_agent | 1d | T1 | deferred (composite) | composite model |
| S-MOD-14a | MODEL | gp_evolved_rule | 1d | T1 | deferred (composite) | evolved rules; every rule is a trial |
| S-MOD-01b | MODEL | hmm_regime | 1d | T1 | deferred (composite) | 3000-day fit window exceeds history |
| S-MOD-01a | MODEL | jump_model_regime | 1d | T1 | deferred (composite) | 3000-day fit window exceeds history |
| S-XS-02b | MODEL | past_return_lag_forecast | 1mo | T1 | grid XS-H | lag 1 collapses onto XS-G |
| S-MR-13a | MODEL | residual_s_score | 1d | T1 | grid XS-P |  |
| S-CAL-14b | TS_STATE | equity_weight_drift_beyond_band | 1d | P | - | equity and bond futures |
| S-FLOW-13a | TS_STATE | fear_greed_index | 1d | P | - | vendor index; thresholds unpublished |
| S-BRK-13a | TS_STATE | gap | 1d | P | - | no session gap in perps |
| S-BRK-13b | TS_STATE | gap | 1d | P | - | no session gap in perps |
| S-MR-14a | TS_STATE | gap | 1d | P | - | no session gap in perps |
| S-BRK-05a | TS_STATE | noise_band_break | 15m | P | - | needs a cash open |
| S-BRK-03a | TS_STATE | opening_bar_sign | 5m | P | - | needs a cash open |
| S-BRK-04a | TS_STATE | opening_range_break | 5m | P | - | US stock intraday |
| S-FLOW-12a | TS_STATE | search_volume_change | 1w | P | - | Google Trends |
| S-BRK-04b | TS_STATE | volume_spike | 5m | P | - | US stock intraday |
| S-BRK-08c | TS_STATE | bollinger_pct_b | 1d | T1 | grid TS-M |  |
| S-MR-03a | TS_STATE | bollinger_pct_b | 1d | T1 | collapsed onto TS-M | = S-BRK-08c, opposite sign |
| S-MR-05a | TS_STATE | cci | 1d | T1 | grid TS-M |  |
| S-MR-05b | TS_STATE | cci | 1d | T1 | grid TS-M |  |
| S-BRK-10a | TS_STATE | channel_breakout | 1d | T1 | collapsed onto TS-F | grid published as ranges only |
| S-TREND-10a | TS_STATE | channel_breakout | 1d | T1 | grid TS-L | ATR(10) x 3 recalled, flagged |
| S-TREND-11a | TS_STATE | channel_breakout | 1d | T1 | grid TS-L |  |
| S-MR-07b | TS_STATE | consecutive_down_days | 1d | T1 | unspecified | N not published |
| S-TREND-08a | TS_STATE | dmi_sign | 1d | T1 | grid TS-K |  |
| S-BRK-09a | TS_STATE | donchian_breakout | 1d | T1 | grid TS-F |  |
| S-BRK-11a | TS_STATE | donchian_breakout | 1d | T1 | collapsed onto TS-F | lookbacks unpublished |
| S-MR-07a | TS_STATE | donchian_breakout | 1d | T1 | grid TS-F | SMA200 gate stripped |
| S-TREND-07a | TS_STATE | donchian_breakout | 1d | T1 | collapsed onto TS-F | = 20 |
| S-TREND-07b | TS_STATE | donchian_breakout | 1d | T1 | collapsed onto TS-F | = 55 |
| S-TREND-07c | TS_STATE | donchian_breakout | 1d | T1 | collapsed onto TS-F | lookback unpublished |
| S-TREND-16a | TS_STATE | donchian_breakout | 1d | T1 | grid TS-F |  |
| S-TREND-06a | TS_STATE | ema_cross | 1d | T1 | grid TS-K |  |
| S-TREND-14a | TS_STATE | heikin_ashi_colour | 1d | T1 | grid TS-K |  |
| S-TREND-13a | TS_STATE | hma_slope | 1d | T1 | grid TS-K |  |
| S-MR-06a | TS_STATE | ibs | 1d | T1 | grid TS-N | no close auction in perps |
| S-TREND-06b | TS_STATE | macd | 1d | T1 | grid TS-K |  |
| S-XS-10b | TS_STATE | market_illiquidity | 1d | T1 | unspecified | expectation model and horizon |
| S-BRK-01b | TS_STATE | open_noise_stretch_break | 1d | T1 | grid TS-N | state at close, 10-day hold |
| S-MR-11a | TS_STATE | pair_spread_zscore | 1d | T1 | grid TS-O |  |
| S-MR-12a | TS_STATE | pair_spread_zscore | 1d | T1 | grid TS-O |  |
| S-MR-16a | TS_STATE | pair_spread_zscore | 5m | T1 | collapsed onto TS-O | 1d variant of a 5m/1h/1d study; formation and trading periods unpublished |
| S-MR-16b | TS_STATE | pair_spread_zscore | 5m | T1 | collapsed onto TS-O | 1d variant of a 5m/1h/1d study; formation and trading periods unpublished |
| S-MOD-07a | TS_STATE | past_return | 1mo | T1 | grid TS-D | on MKT_A10 |
| S-MOD-11b | TS_STATE | past_return | 1d | T1 | grid TS-B |  |
| S-MR-10a | TS_STATE | past_return | 1d | T1 | grid TS-E | on MKT_A10 |
| S-TREND-01a | TS_STATE | past_return | 1mo | T1 | grid TS-A | 36-month hold infeasible |
| S-TREND-02a | TS_STATE | past_return | 1mo | T1 | grid TS-A |  |
| S-TREND-02b | TS_STATE | past_return | 1mo | T1 | grid TS-A |  |
| S-TREND-02c | TS_STATE | past_return | 1mo | T1 | collapsed onto TS-A | duplicate of S-TREND-01a |
| S-TREND-15a | TS_STATE | past_return | 1w | T1 | grid TS-C |  |
| S-TREND-03a | TS_STATE | price_vs_sma | 1mo | T1 | grid TS-J |  |
| S-MR-04a | TS_STATE | price_zscore | 1d | T1 | grid TS-N |  |
| S-MR-01a | TS_STATE | rsi | 1d | T1 | grid TS-M | SMA200 gate stripped |
| S-MR-02a | TS_STATE | rsi | 1d | T1 | grid TS-M |  |
| S-TREND-04a | TS_STATE | sma_cross | 1d | T1 | grid TS-G |  |
| S-TREND-04b | TS_STATE | sma_cross | 1d | T1 | grid TS-H |  |
| S-TREND-05a | TS_STATE | sma_cross | 1d | T1 | grid TS-I |  |
| S-MOD-02a | TS_STATE | spread_zscore | 1d | T1 | grid TS-O | pairs from S-MR-11a |
| S-MR-02b | TS_STATE | stochastic | 1d | T1 | collapsed onto TS-M | 14 = S-MR-02c; 5 and 9 lack an extreme level |
| S-MR-02c | TS_STATE | stochastic | 1d | T1 | grid TS-M |  |
| S-TREND-12a | TS_STATE | tenkan_kijun_cross | 1d | T1 | grid TS-K |  |
| S-FLOW-05a | TS_STATE | volume_spike | 1d | T1 | grid XS-S | own-volume spike, long-short |
| S-FLOW-05b | TS_STATE | volume_spike | 1w | T1 | grid XS-T |  |
| S-BRK-07b | TS_STATE | asian_range_break | 1h | T2 | - | 1h, UTC windows |
| S-BRK-06b | TS_STATE | open_k_prior_range_break | 1d | T2 | - | 1h for an honest intraday entry |
| S-BRK-06a | TS_STATE | open_k_prior_range_break | 5m | T3 | - | 5m |
| S-MOD-09b | TS_STATE | past_return | 1m | T3 | - | 1m |
| S-MR-15b | TS_STATE | past_return | 15m | T3 | - | 15m |
| S-PAT-13a | TS_STATE | pnf_double_top_breakout | 1m | T3 | - | 1m; box size unpublished |
| S-PAT-13b | TS_STATE | renko_brick_direction | 1m | T3 | - | 1m; brick size unpublished |
| S-MR-08a | TS_STATE | vwap_distance | 1m | T3 | - | 1m |
| S-TREND-08b | VOL_STATE | adx | 1d | T1 | grid V-A |  |
| S-BRK-08a | VOL_STATE | bollinger_bandwidth_low | 1d | T1 | grid V-B |  |
| S-MOD-06b | VOL_STATE | changepoint_severity | 1d | T1 | deferred (composite) | GP changepoint feature |
| S-MOD-01c | VOL_STATE | downside_deviation | 1d | T1 | deferred (composite) | jump-model feature, no threshold |
| S-BRK-14b | VOL_STATE | ewma_vol | 1d | T1 | grid V-H |  |
| S-TREND-01b | VOL_STATE | ewma_volatility | 1d | T1 | grid V-H |  |
| S-BRK-02b | VOL_STATE | inside_bar | 1d | T1 | grid V-D |  |
| S-BRK-01a | VOL_STATE | narrow_range_nr_n | 1d | T1 | grid V-F | NR range -> NR4/NR7 |
| S-BRK-02a | VOL_STATE | narrow_range_nr_n | 1d | T1 | grid V-E |  |
| S-MOD-04a | VOL_STATE | realised_variance | 1d | T1 | grid V-H |  |
| S-BRK-14a | VOL_STATE | realized_variance | 1d | T1 | collapsed onto V-H | = S-MOD-04a |
| S-TREND-04c | VOL_STATE | sma_cross | 1d | T1 | grid V-G |  |
| S-BRK-08b | VOL_STATE | ttm_squeeze | 1d | T1 | grid V-C |  |
| S-FLOW-04a | VOL_STATE | vpin | 1m | T3 | - | 1m |
| S-XS-16a | XS_RANK | address_growth | 1d | P | - | on-chain addresses |
| S-CARRY-11a | XS_RANK | basis | 1mo | P | - | commodity curves |
| S-CARRY-12a | XS_RANK | basis | 1mo | P | - | equity index futures |
| S-CARRY-13a | XS_RANK | bond_carry | 1mo | P | - | bond yields |
| S-CAL-12b | XS_RANK | earnings_surprise_sue | 1d | P | - | earnings |
| S-CAL-12a | XS_RANK | earnings_surprise_sue_ear | 1d | P | - | earnings |
| S-CARRY-08a | XS_RANK | forward_discount | 1mo | P | - | FX forwards |
| S-BRK-16a | XS_RANK | implied_vol_of_vol | 1d | P | - | implied vol |
| S-XS-04a | XS_RANK | industry_past_return | 1mo | P | - | coin sector map |
| S-XS-11a | XS_RANK | market_cap | 1mo | P | - | market cap |
| S-XS-11b | XS_RANK | market_cap | 1mo | P | - | book-to-market |
| S-XS-12b | XS_RANK | market_cap | 1d | P | - | market cap |
| S-MR-09b | XS_RANK | past_return | 1d | P | - | industry portfolios |
| S-XS-16b | XS_RANK | price_to_new_address | 1d | P | - | on-chain addresses |
| S-CARRY-07a | XS_RANK | staking_yield | 1w | P | - | staking yields |
| S-XS-10a | XS_RANK | amihud_illiquidity | 1d | T1 | infeasible | 1-year formation and hold: 4 windows |
| S-XS-06a | XS_RANK | beta | 1d | T1 | grid XS-N |  |
| S-XS-05a | XS_RANK | distance_to_high | 1d | T1 | grid XS-J |  |
| S-XS-14a | XS_RANK | distance_to_high | 1d | T1 | grid XS-K | volume-only split: all perps Large&Liquid |
| S-XS-12c | XS_RANK | dollar_volume | 1d | T1 | unspecified | volume window |
| S-CARRY-05a | XS_RANK | funding_rate | 8h | T1 | grid XS-R | funding file needed for every U50A coin |
| S-MR-06b | XS_RANK | ibs | 1d | T1 | grid XS-Q | no close auction in perps |
| S-XS-07a | XS_RANK | idiosyncratic_vol | 1d | T1 | grid XS-M | residuals vs MKT_A10 |
| S-XS-08a | XS_RANK | max_daily_return | 1d | T1 | grid XS-L |  |
| S-MOD-08a | XS_RANK | past_return | 1d | T1 | deferred (composite) | ML ensemble over 31 lookbacks |
| S-MOD-10b | XS_RANK | past_return | 1d | T1 | collapsed onto XS-B | lookbacks unpublished |
| S-MR-09a | XS_RANK | past_return | 1d | T1 | grid XS-F |  |
| S-MR-15a | XS_RANK | past_return | 1d | T1 | grid XS-G | 1d and 1w collapse onto XS-F, XS-B |
| S-XS-01a | XS_RANK | past_return | 1d | T1 | grid XS-A |  |
| S-XS-02a | XS_RANK | past_return | 1d | T1 | grid XS-C | no-skip collapses onto XS-B |
| S-XS-12a | XS_RANK | past_return | 1d | T1 | grid XS-B |  |
| S-XS-13a | XS_RANK | past_return | 1d | T1 | grid XS-B | volume-only split |
| S-XS-13b | XS_RANK | past_return | 1d | T1 | grid XS-E |  |
| S-XS-13c | XS_RANK | past_return | 1d | T1 | grid XS-D |  |
| S-XS-15a | XS_RANK | past_return | 1d | T1 | grid XS-I | size split dropped |
| S-XS-03a | XS_RANK | residual_return | 1mo | T1 | grid XS-O | residuals vs MKT_A10 |
| S-MR-15c | XS_RANK | past_return | 4h | T2 | - | 12h returns |
| S-CARRY-05b | XS_RANK | funding_change | 5m | T3 | - | 5m |
| S-CAL-06a | XS_RANK | past_session_return | 15m | T3 | - | session boundary at :30 UTC |
| S-XS-09a | XS_RANK | realized_skewness | 1m | T3 | - | intraday interval unspecified (1m on card) |

## 3. Task B: the standard grid

### 3.1 Universe, market proxy, conventions

- **U50A** (the universe for every T1 cell): each day, the 50 half-A coins with the highest median
  daily quote volume over the 30 days ending t-1, among coins that traded (volume > 0) on t-1 and have
  at least 90 live days. Fewer than 50 when fewer qualify. Ranked within half A only. Names per day:
  11.3 (2020), 43.5 (2021), 49.9 (2022), 50 (2023-24); the first day with at least 10 names is
  2020-05-09. Within-half rank 50 is about overall rank 100, so the 13 bp BTC-grade cost is optimistic
  for the bottom of U50A (net is reported at 1x, 1.5x and 2x cost).
- **MKT_A10**: equal-weight return of the 10 top U50A coins (section 6). Used for the market hedge
  (`information_test(mkt_ret=...)`), residual models and all regimes.
- **Timing**: decide at the close of the 1d bar stamped t, enter at the open of t+1, exit at the open
  of t+1+h (`measure.trade_return`). Cost 13 bp round trip per leg; real funding.

### 3.2 Grid rules (all fixed before any data are read)

- **G1. Published values only.** No extension, no interpolation. A card that publishes a range and not
  values adds no values of its own; it collapses onto values other cards published inside its range.
- **G2. Holds.** The card's published fixed hold. Where the card says "signal_defined" or gives no
  hold, the common set for its bar: 1d bars {1, 7, 30} days; 1w bars {1, 4} weeks; 1mo bars {1} month.
  The signal-defined exit is wrapper and is stripped.
  Why {1, 7, 30}: one horizon per horizon band of CATALOGUE section 2 (P1a up to a day, P1b days to
  weeks, P1c a month), so a sign flip between bands is visible, which is the question that split P1;
  calendar units because perps trade 7 days a week; about 4-5x apart, so adjacent horizons share
  little (the h-day return windows overlap with correlation sqrt(1/7) = 0.38 and sqrt(7/30) = 0.48);
  30 days is the longest horizon with more than 50 non-overlapping explore windows (56). Three is the
  fewest that can show a sign flip.
- **G3. Collapse key** = (archetype, variable, parameters, hold, universe type). A "with-state" and
  an "against-state" probe on the same key are ONE cell: the cell reports the signed effect, and each
  card's direction claim says only which sign it predicted. The weekday anchor of a weekly sort is not
  part of the key unless the card's variant depends on it (XS-C).
- **G4. Wrappers stripped**: gates (close above SMA200), stops, targets, confirmation bars, exits.
- **G5. Pattern families pooled per card**: one bullish-versus-bearish cell per hold. Per-pattern views
  are not computed in phase 2.
- **G6. Composite models deferred** to phase 3.
- **G7. A missing non-hold parameter means no cell** (5 probes), until the chair re-reads the source.
- **G8. Feasibility**: a cell with fewer than 12 independent explore windows is not run (Halloween:
  4 seasons; turn of year: 4 Januaries; Amihud 1-year formation and hold: 4 windows; TSMOM 36-month
  hold). F-A runs only if its outcome-blind funnel reaches 12 windows.
- **Computed per cell**: the pooled two-sided statistic and the pre-stated regime breakdown. Nothing
  else: no long/short leg split, no per-coin view, no per-pattern view. What is not computed cannot be
  selected.

### 3.3 Grid

H1 = {1, 7, 30} days. Class = what the sealed set could resolve (section 4.5): R resolvable, L large
effects only, D descriptive only. Time-series families are classed on their market-hedged read; their
raw directional read is L at 1 day and D beyond.

| family | archetype | probes | state | published parameters | holds | cells | R / L / D |
|---|---|---|---|---|---|---|---|
| TS-A | TS_STATE | S-TREND-01a, 02a, 02b, 02c | sign of past return, month-end decisions | L = 1, 3, 12 months | 1 month | 3 | 0/0/3 |
| TS-B | TS_STATE | S-MOD-11b | sign of 12-month return, daily decisions | L = 12 months | 1, 7 d (30 d = TS-A) | 2 | 1/1/0 |
| TS-C | TS_STATE | S-TREND-15a | weekly return in top / bottom quintile of the coin's first 104 weeks | L = 1 week | 1, 2, 3, 4 weeks | 4 | 0/2/2 |
| TS-D | TS_STATE | S-MOD-07a | 4 states of (12-month sign, 1-month sign) on MKT_A10 | 12, 1 months | 1 month | 3 contrasts | 0/0/3 |
| TS-E | TS_STATE | S-MR-10a | -(4r_t + 3r_t-1 + 2r_t-2 + r_t-3) on MKT_A10 | weights 4,3,2,1 | 1 d | 1 | 0/0/1 |
| TS-F | TS_STATE | S-TREND-16a, S-BRK-09a, S-MR-07a (S-TREND-07a/b/c, S-BRK-10a, S-BRK-11a, S-BRK-10b collapsed) | close is the highest (+1) / lowest (-1) close of the last L bars | L = 5, 7, 10, 20, 30, 55, 60, 90, 150, 250, 360 | H1 | 33 | 11/11/11 |
| TS-G | TS_STATE | S-TREND-04a | SMA(f) above / below SMA(s) by more than band b | (f,s) = (1,50), (1,150), (5,150), (1,200), (2,200); b = 0, 1 % | 1 d | 10 | 10/0/0 |
| TS-H | TS_STATE | S-TREND-04b | crossover event of the same 10 rules | as TS-G | 10 d | 10 | 0/10/0 |
| TS-I | TS_STATE | S-TREND-05a | SMA50 above / below SMA200 | 50, 200 | H1 | 3 | 1/1/1 |
| TS-J | TS_STATE | S-TREND-03a | month-end close above / below its 10-month SMA | 10 months | 1 month | 1 | 0/0/1 |
| TS-K | TS_STATE | S-TREND-06a, 06b, 12a, 08a, 13a, 14a | EMA12 vs EMA26 state; MACD(12,26,9) signal cross; Tenkan(9)/Kijun(26) cross; +DI vs -DI (14, Wilder); HMA(20) slope sign; Heikin-Ashi colour | as listed | H1 | 18 | 6/6/6 |
| TS-L | TS_STATE | S-TREND-11a, 10a | close beyond SMA10(typical) +- SMA10(range); close beyond (H+L)/2 +- 3 ATR(10) (recalled values, flagged) | 10; 10 and 3 | H1 | 6 | 2/2/2 |
| TS-M | TS_STATE | S-BRK-08c, S-MR-03a, 05a, 05b, 01a, 02a, 02c (02b collapsed) | %b(20,2) beyond 0/1; CCI(20) beyond +-100; CCI re-entry inside +-200; RSI(2) below 5 / above 95; RSI(2) below 10 / above 95; RSI(14) crosses back through 30 / 70; Williams %R(14) beyond -80 / -20 | as listed | H1 | 21 | 7/7/7 |
| TS-N | TS_STATE | S-MR-04a, S-MR-06a, S-BRK-01b | price z-score with half-life lookback (expanding OLS); IBS below 0.2 / above 0.8; close beyond open +- 2 x SMA10 of min(H-O, O-L) | as listed | 1 d; 1 d; 10 d | 3 | 2/1/0 |
| TS-O | TS_STATE (pairs) | S-MR-11a, S-MR-12a, S-MOD-02a (16a/b collapsed) | spread beyond 2 formation sd; distance pairs (12-month formation, 6-month trading, lag 1); Engle-Granger pairs; Kalman hedge ratio on the top-5 distance pairs | distance: top 5, 20 pairs; EG: 5, 10, 20, 40 pairs x 1, 5, 10 % ; Kalman delta 1e-4, R 1e-3, 1 sd | H1 | 45 | 15/15/15 |
| XS-A | XS_RANK | S-XS-01a | J-month return, skip 0 or 1 week, deciles, overlapping monthly cohorts | J, K = 3, 6, 9, 12 months | K | 32 | 0/0/32 |
| XS-B | XS_RANK | S-XS-12a, 13a (+ S-MR-15a 1w, S-XS-02a no-skip, S-MOD-10b) | L-week return, quintiles | L = 1, 2, 3, 4, 12, 26 weeks | 1 week | 6 | 0/6/0 |
| XS-C | XS_RANK | S-XS-02a | Wednesday-Monday return (skip Tuesday) | 1 week | 1 week | 1 | 0/1/0 |
| XS-D | XS_RANK | S-XS-13c | 2-week return | 2 weeks | 2 weeks | 1 | 0/1/0 |
| XS-E | XS_RANK | S-XS-13b | 14-day return within the liquid and the illiquid 30 % (Amihud, same 14 days) | 30/40/30 x 30/40/30 | 14 d | 2 contrasts | 0/2/0 |
| XS-F | XS_RANK | S-MR-09a (+ S-MR-15a 1d) | 1-day return | 1 d | 1 d | 1 | 1/0/0 |
| XS-G | XS_RANK | S-MR-15a (+ S-XS-02b lag 1) | 1-month return | 1 month | 1 month | 1 | 0/0/1 |
| XS-H | XS_RANK | S-XS-02b | return of month t-12 | lag 12, deciles | 1 month | 1 | 0/0/1 |
| XS-I | XS_RANK | S-XS-15a | minus the 52-week return, 30/40/30 (size split dropped) | 52 weeks | 1 week | 1 | 0/1/0 |
| XS-J | XS_RANK | S-XS-05a | close / prior 52-week high, 30 %, 1-month skip (recalled, flagged) | 52 weeks | 6 months | 1 | 0/0/1 |
| XS-K | XS_RANK | S-XS-14a | ln close - ln max high over h weeks (all perps are Large&Liquid by the volume rule) | h = 1, 2, 4, 12, 26 weeks | 1 week | 5 | 0/5/0 |
| XS-L | XS_RANK | S-XS-08a | mean of the N largest daily returns of the prior month, deciles | N = 1..5 | 1 month | 5 | 0/0/5 |
| XS-M | XS_RANK | S-XS-07a | idiosyncratic vol vs MKT_A10 (formation/gap/hold) | 1/0/1, 1/1/1, 12/1/12 months | as listed | 3 | 0/0/3 |
| XS-N | XS_RANK | S-XS-06a | shrunk beta (1-year vol, 5-year 3-day correlation, at least 750 d), median split | as published | 1 month | 1 | 0/0/1 |
| XS-O | XS_RANK | S-XS-03a | residual momentum vs MKT_A10 (36-month regression, score t-12..t-2), deciles | as published | 1, 3, 6, 12 months | 4 | 0/0/4 |
| XS-P | XS_RANK | S-MR-13a | PCA residual s-score (15 PCs of 252 d, 60-d OU), open at +-1.25 | as published | H1 | 3 | 1/1/1 |
| XS-Q | XS_RANK | S-MR-06b | IBS, long lowest / short highest single name | k = 1 a leg | 1 d | 1 | 0/1/0 |
| XS-R | XS_RANK | S-CARRY-05a | last settled f8 before the decision; long low, short high | quintiles | H1 | 3 | 1/1/1 |
| XS-S | XS_RANK | S-FLOW-05a | own 50-day dollar-volume rank (high >= 46, low <= 5), non-overlapping 50-day formation | 50 days | 1, 10, 20 d | 3 | 0/0/3 |
| XS-T | XS_RANK | S-FLOW-05b | own 10-week dollar-volume rank (10 vs 1) | 10 weeks | 20 d | 1 | 0/0/1 |
| V-A | VOL_STATE | S-TREND-08b | ADX(14) below 20; above 40 | 14; 20, 40 | H1 | 6 | 4/0/2 |
| V-B | VOL_STATE | S-BRK-08a | BB(20,2) bandwidth within 3 % of its 125-day low | as listed | H1 | 3 | 2/0/1 |
| V-C | VOL_STATE | S-BRK-08b | TTM squeeze fires (BB 20/2 leaves Keltner 20/1.5) | as listed | H1 | 3 | 2/0/1 |
| V-D | VOL_STATE | S-BRK-02b | inside bar; ID/NR4 | | H1 | 6 | 4/0/2 |
| V-E | VOL_STATE | S-BRK-02a | NR4; NR7 | 4, 7 | H1 | 6 | 4/0/2 |
| V-F | VOL_STATE | S-BRK-01a | NR4; NR7 | 4, 7 (inside the published 2-19) | 10 d | 2 | 0/2/0 |
| V-G | VOL_STATE | S-TREND-04c | next-day abs return on sell vs buy days of the 10 BLL rules | as TS-G | 1 d | 10 | 10/0/0 |
| V-H | VOL_STATE | S-BRK-14b, S-TREND-01b, S-MOD-04a (+14a) | vol-managed MKT_A10: alpha of w = c / sigma-hat exposure on the unscaled index | EWMA half-life 10, 20, 90 d (t-2 lag), daily; EWMA com 60, monthly; prior-month RV, monthly | 1 d; 1 month | 5 | 0/0/5 |
| L-A | LEVEL_TOUCH | S-PAT-01a | 4 three-day reversal patterns and mirrors, pooled, 3-day-MA trend rule | as published | 1, 2, 3 d | 3 | 3/0/0 |
| L-B | LEVEL_TOUCH | S-PAT-01b | 28 candle signals pooled into single-line and reversal families, 10-day EMA trend | hammer shadow 2x body | 10 d | 2 | 0/2/0 |
| L-C | LEVEL_TOUCH | S-PAT-02a | 10 kernel-regression chart patterns pooled bullish vs bearish | window 38, bandwidth 0.3 CV, lag 3 | 1 d | 1 | 1/0/0 |
| L-D | LEVEL_TOUCH | S-PAT-02b | head-and-shoulders (and inverse) with neckline break | 63-day window, 1.5 / 4 % tolerance | 20, 40, 60 d | 3 | 0/0/3 |
| L-E | LEVEL_TOUCH | S-BRK-02c | close beyond the setup bar's extreme after NR4, NR7, ID/NR4, inside bar | 4 setups | H1 | 12 | 4/4/4 |
| C-A | CLOCK | S-CAL-01a | turn of month: days -1..+3 of the UTC month boundary, on MKT_A10 | as published | 4-day window | 1 | 0/0/1 |
| C-B | CLOCK | S-CAL-02a | weekend (Sat, Sun UTC) vs weekdays, on MKT_A10 | | 1 d | 1 | 0/0/1 |
| F-A | FLOW_STATE | S-FLOW-10b | 30-day mean funding below 0, long | 30 d | 90 d | 1 | 0/0/1 |

### 3.4 Totals

| archetype | cells | R | L | D |
|---|---|---|---|---|
| TS_STATE | 163 | 55 | 56 | 52 |
| XS_RANK | 76 | 3 | 19 | 54 |
| VOL_STATE | 41 | 26 | 2 | 13 |
| LEVEL_TOUCH | 21 | 8 | 6 | 7 |
| CLOCK | 2 | 0 | 0 | 2 |
| FLOW_STATE | 1 | 0 | 0 | 1 |
| **total** | **304** | **92** | **83** | **129** |

Regime views (section 6): 16 levels per cell (trend 2, volatility 3, funding 3, liquidity 3, year 5),
plus 3 dispersion levels for the 76 XS cells: **5,092 views**. Phase 3 selects from views, so phase 3 is
charged for them (section 5.2).

### 3.5 Why 304, and why not cut further

- **It is every published T1 value after collapse.** The only reductions (G5-G8) are made without data.
  A smaller grid would require us to choose which published values to drop, which is itself a free
  parameter; a larger one would extend published grids.
- **The trial count is not the binding cost.** The expected maximum |t| of N independent null cells is
  about 2.77 (N = 100), 3.11 (N = 304) and 3.87 (the 5,092 views). The cells are nested and correlated
  (33 Donchian lookbacks, 36 cointegration cells nested in pair count and confidence), so the effective
  N is nearer 100. Either way, an explore t of about 3 is what the best null cell reaches. Explore
  results can rank primitives; they cannot support a claim.
- **The binding constraint is the sealed set** (section 4): 129 of the 304 cells could never be
  confirmed whatever they show. They stay in because the catalogue's goal is a map of what primitives
  exist and when, and a sign or size estimate with a wide interval is still part of the map. They are
  flagged descriptive only and cannot be nominated.
- **If logged as proposed in section 5.2**, the 304 cells do not raise the deflated-Sharpe bar of
  unrelated edge-lab work.

## 4. Task C: power by archetype

### 4.1 Inputs (explore quadrant, U50A unless stated, bp)

| quantity | 1 d | 7 d | 30 d | note |
|---|---|---|---|---|
| sd of single-coin h-day return | 659 | 1,812 | 4,761 | raw; kurtosis 187 / 49 / 76 |
| same, winsorised 0.5 / 99.5 % | 592 | 1,623 | 4,032 | sensitivity only |
| same, 1.4826 x MAD | 436 | 1,194 | 2,565 | sensitivity only |
| same-date intra-class correlation rho | 0.483 | 0.442 | 0.386 | ANOVA over dates |
| sd of MKT_A10 (non-overlapping) | 453 | 1,190 | 3,236 | |
| sd of placebo quintile spread, 10 names a leg | 241 | 727 | 1,905 | hash sort, rebalanced every h |
| sd of abs h-day return | 501 | 1,391 | 3,966 | VOL_STATE noise |
| corr of two random sub-halves' EW indices | 0.94 | 0.94 | 0.95 | proxy for half A vs half B |
| all half-A coins with 90 days of history: sd / rho | 629 / 0.49 | 1,730 / 0.46 | 4,462 / 0.41 | wider universe, similar |

### 4.2 Usable history per quadrant

| quadrant | coins with days | coin-days | calendar days | live coins (2020-07 / 2021-07 / 2022-07 / 2023-07 / 2024-07 / 2025-07 / 2026-06) | windows for U50 (1 d / 7 d / 30 d) |
|---|---|---|---|---|---|
| explore (early, A) | 191 | 135,228 | 1,827 | 15 / 56 / 69 / 91 / 133 / - / - | 1,698 / 244 / 56 (from 2020-05-09) |
| early_B | 199 | 137,774 | 1,827 (same dates) | 15 / 58 / 70 / 93 / 131 / - / - | assumed 1,698 / 244 / 56 |
| late_A | 336 | 153,618 | 638 | - / - / - / - / - / 217 / 270 | 638 / 91 / 21 |
| late_B | 330 | 153,060 | 638 (same dates as late_A) | - / - / - / - / - / 223 / 260 | 638 / 91 / 21 |

Sealed share of coin-days 76.7 %; sealed share of NEW calendar dates 638 of 2,465 (26 %). Explore
names per day by year: 11 (2020), 44, 50, 50, 50. Per-cell history limits inside explore: 12-month
lookbacks start about 2021-01 (18.7 U50A coins a day with a year of history in 2021, 40 in 2022); the
750-day beta window (XS-N) has 14.9 eligible names a day on average in 2022 and none before; the
36-month residual model (XS-O) has at least 10 names only from about mid-2023; funding exists for 34-39 U50A coins a day. Open interest (T2) for
alts starts 2021-12, so its explore window is 2022-03 to 2024-12 (H010).

### 4.3 Noise models (assumptions labelled)

- **M1, market-exposed** (raw time-series states pooled across coins, CLOCK, EVENT, MKT_A10 timing):
  the window mean of m same-window trades has sd = sigma_h x sqrt(rho_h + (1 - rho_h)/m). Sign states
  (every coin-day long or short): m = 44 explore, 100 late (both halves on the same dates). Extreme
  states: fire on 5 % of coin-days, independently across coins (optimistic; clustered states are worse).
  Sealed read: late era only (finding 2). The "pooled" column is shown only to show what a naive read
  would claim.
- **M2, market-neutral** (XS spreads, pairs, hedged time-series alpha): XS window sd = placebo spread
  sd x 1.5 (ASSUMPTION: a real sort loads on factors; the placebo carries none). Deciles x sqrt(2).
  Hedged TS: residual sd = placebo spread sd / sqrt(2/10), residual same-date correlation 0.05
  (ASSUMPTION). In the late era the two halves give two spreads a date, correlated 0.5 (ASSUMPTION).
  Sealed read: pooled over late_A, early_B, late_B.
- **Sealed sd = explore sd** (ASSUMPTION; 2025-26 cannot be looked at). Every MDE scales linearly with
  it: a sealed era 30 % calmer gives MDEs 30 % smaller.
- **Cost-viable gross** = 3 x round trip: 39 bp per single-leg trade; 78 bp per two-leg trade or
  full-turnover long-short rebalance (2 x 13 bp).
- MDE = `power.min_detectable_edge_bps(n_windows, window_sd, t_bar, power=0.8)`; pooled sealed reads
  use the pooled n and the n-weighted window variance. t bars: 2.0 explore; 2.576 sealed
  (`ledger.bonferroni_t(5)`, section 5.1).

### 4.4 Minimum detectable gross edge (bp per trade or per rebalance, 80 % power)

| archetype | case | h (d) | explore, t 2 | sealed pooled, t 2.58 | sealed late only, t 2.58 | cost-viable gross |
|---|---|---|---|---|---|---|
| TS_STATE raw | sign state | 1 | 32 | (33) | **62** | 39 |
| TS_STATE raw | extreme state, 5 % | 1 | 41 | (40) | **69** | 39 |
| TS_STATE raw | sign state | 7 | 222 | (228) | **434** | 39 |
| TS_STATE raw | extreme state, 5 % | 7 | 229 | (234) | **441** | 39 |
| TS_STATE raw | sign state | 30 | 1,143 | (1,169) | **2,223** | 39 |
| TS_STATE raw | extreme state, 5 % | 30 | 1,149 | (1,174) | **2,228** | 39 |
| TS_STATE hedged | sign state | 1 | 10 | **10** | 18 | 78 |
| TS_STATE hedged | extreme state, 5 % | 1 | 26 | **25** | 36 | 78 |
| TS_STATE hedged | sign state | 7 | 79 | **79** | 142 | 78 |
| TS_STATE hedged | extreme state, 5 % | 7 | 103 | **101** | 166 | 78 |
| TS_STATE hedged | sign state | 30 | 433 | **434** | 775 | 78 |
| TS_STATE hedged | extreme state, 5 % | 30 | 450 | **449** | 792 | 78 |
| XS_RANK | quintile, 10 a leg | 1 | 25 | **25** | 42 | 78 |
| XS_RANK | decile, 5 a leg | 1 | 35 | **35** | 60 | 78 |
| XS_RANK | quintile | 7 | 198 | **197** | 338 | 78 |
| XS_RANK | decile | 7 | 281 | **278** | 479 | 78 |
| XS_RANK | quintile | 30 | 1,085 | **1,074** | 1,845 | 78 |
| XS_RANK | decile | 30 | 1,534 | **1,519** | 2,610 | 78 |
| CARRY (XS funding) | quintile, 7 a leg | 1 / 7 / 30 | 30 / 237 / 1,297 | **30 / 235 / 1,284** | 51 / 404 / 2,206 | 78 |
| VOL_STATE | abs return after a 15 % state | 1 / 7 / 30 | 26 / 182 / 1,077 | **27 / 186 / 1,103** | 49 / 355 / 2,102 | none (conditioner) |
| CLOCK (MKT_A10) | weekend vs weekday, per day | 1 | 69 | (71) | **136** | 39 |
| CLOCK (MKT_A10) | turn of month vs rest, per day | 1 | 92 | (95) | **181** | 39 |
| CLOCK (T2) | one pre-stated hour vs rest, per hour (hourly sd = daily / sqrt 24, ASSUMPTION) | 1 h | 7 | (7) | **13** | 39 |
| EVENT (T2) | FOMC days, 8 a year | 1 | 214 | (219) | **413** | 39 |
| EVENT (T2) | CPI + NFP + FOMC days, about 32 a year | 1 | 110 | (113) | **217** | 39 |
| FLOW_STATE (T2) | OI-tail flush, 50-100 coins (ASSUMED 50 explore / 20 late dates) | 1 | 228 | (232) | **434** | 39 |
| FLOW_STATE (T2) | OI-tail flush, 8 coins (H010 counts: 25 / 9 dates) | 1 | 323 | (333) | **647** | 39 |

Bold = the column that decides the sealed verdict for that form. Brackets = invalid for that form
(early_B duplicates explore's market path).

For scale: the sealed late era resolves a market-timing annual Sharpe of 2.58 (t 2.58) or 2.15 (t 2);
with early_B wrongly counted as independent it would be 1.35. A Sharpe of 1.0 needs 11.7 years and 0.5
needs 47 years (`power.years_for_sharpe`).

### 4.5 What can and cannot be resolved

- **Resolvable (MDE at or below the cost-viable gross)**: market-neutral forms at 1-3 day holds:
  XS spreads (25-35 bp vs 78), pairs, PCA residuals, cross-sectional funding (30 vs 78), market-hedged
  time-series alpha (10-25 vs 78); VOL_STATE at 1 and 7 days as a conditioner of size (vol effects
  are typically a large fraction of the mean abs return: 429 bp at 1 d, 1,167 bp at 7 d).
- **Large effects only**: market-neutral 7-14 day holds (hedged TS 79-101 vs 78; XS 197-278, so a
  weekly spread must be about 2.5-3.5x cost-viable); raw time-series at 1 day (late-only MDE 62-69 vs
  39); single-name-per-leg sorts.
- **Descriptive only, flagged in every report**: every hold of 20 days or more and every
  monthly-decision cell (XS momentum J/K, MAX, IVOL, BAB, residual momentum, TSMOM, 10-month SMA,
  vol-managed monthly); raw directional time-series beyond 1 day; CLOCK and EVENT (market-wide: only
  638 new dates, so the late-only MDE is 136-181 bp a day, 3.5-4.6x the cost-viable 39 bp);
  FLOW_STATE OI-tail flushes (H010's +100 bp claim is below a 434 bp MDE); funding below zero with a
  90-day hold (F-A); the hour-of-day effect is statistically resolvable (13 bp) but its published size
  (about 9-11 bp, CATALOGUE section 7) is below one 13 bp round trip, so it is sub-cost.
- **T2 carry (cash-and-carry, S-CARRY-01a)**: the price leg is the basis change, so per-month noise is
  small and resolvable in principle; but H001 counted only 8 of 82 sealed-era tail episodes with a spot
  hedge. Count hedgeable episodes before pre-registering it.

## 5. Task D: sealed-open rules

### 5.1 How many opens, and the bar

**Recommendation: at most 5 combinations, opened in ONE batch, all nominated and pre-registered before
the first is opened. Bar: clustered t >= `ledger.bonferroni_t(5)` = 2.576, fixed now, whatever the
batch size turns out to be.**

- Why one batch. The sealed quadrants are one data set. Once batch 1 is read, the team knows how
  primitives behaved in 2025-26 and in half B, and any later nomination is chosen with that knowledge.
  A second batch on the same sealed data would be contaminated by the first. Unused opens are
  forfeited; later ideas go to the forward paper period.
- Why 5. The cost of each extra open is small and logarithmic (bonferroni_t: 1.96 for 1, 2.39 for 3,
  2.58 for 5, 2.81 for 10, 3.02 for 20; every MDE scales with t + 0.84: +6 % from 3 to 5 opens, +13 %
  from 3 to 10). The supply is small: section 4.5 leaves 92 resolvable cells, and the nomination rules
  below will pass few. Five covers the distinct mechanisms (for example a cross-sectional reversal, a
  carry spread, a hedged trend state, a vol-conditioned variant) without inviting near-duplicates.
- Why fixed at 5 and not at the number nominated: so the bar cannot be lowered by nominating fewer.
- With n_trials = 5, the deflated-Sharpe bar of 0.95 corresponds to an unclustered t of about 2.84
  (`ledger.deflated_sharpe`, var_sr = 1/T), slightly stricter than 2.576; both apply.

### 5.2 Global trial count or opens only?

**Recommendation: the t-bar and the deflated-Sharpe bar of the sealed read use the number of sealed
opens (5), not `ledger.total_trials()`. The global count is reported beside every sealed result, not
used as a bar.**

Reasoning. Multiple-testing corrections answer "how many tests were run on THESE data". Every
phase-2/3 trial is run on the explore quadrant; the sealed quadrants see exactly 5 tests. A selected
combination read once on independent data is a fresh test of a pre-stated hypothesis, and its
family-wise error is controlled by the 5. Charging the 300-5,000 explore looks to the sealed read would
double-count selection the holdout already removes. In numbers: DSR >= 0.95 needs t of about 2.84 with
N = 5, 4.06 with N = 71 (today's total), and 4.62 with N = 375 (after logging 304 cells). A 4.6 bar
would push the daily XS MDE from 25 to 40 bp and the 7-day market-neutral MDEs from 79-197 bp to
126-315 bp, for no statistical reason.

What can still leak, so the holdout is not perfectly independent (each item goes into the prereg and
the verdict):

1. **early_B shares explore's dates.** Market paths correlate about 0.94. Handled by reading directional
   forms on the late era only; for market-neutral forms the date-common part of a factor spread (the
   same factor's return in half A and half B on one date) still transfers, which is why the late era
   alone must also have the predicted sign and positive net.
2. **late_A shares explore's coins.** Persistent coin traits are legitimate; coin-specific data
   defects and listing artefacts persist too.
3. **The late era is public history.** Anyone on the team, and the user, knows roughly what crypto did
   in 2025-26. A combination can be steered by hindsight (for example "short alts when funding is high"
   chosen because one remembers alts falling). The nomination must cite explore evidence only, and the
   chair records for each nominee whether its mechanism or regime matches known 2025-26 events.
4. **Earlier repo work already read the sealed era.** H001 counted 2025-26 funding-tail episodes on both
   halves (and found they moved to perp-only listings); H010 counted 2025-26 OI-tail days for 8 alts plus
   BTC and ETH; the v0.10-v0.35 ledger used ETH, XRP, BNB, ADA, DOGE (half A) and BTC, SOL, LINK
   (half B) 5m-1h data through 2026-08 (for example v0.18 carry, v0.22-v0.26 supply/demand). A
   nominee whose mechanism was tested there carries a "touched" flag.
5. **The split used lifetime median volume,** which includes late-era volume. Harmless for returns, but
   a coin's late liquidity shaped its pairing. Rank within half for every phase-2 universe.
6. **Regime frequencies of the sealed era must not be computed before the open** (they need sealed
   prices). Plan power with explore frequencies.
7. **A bug fixed after the open is a second look.** Allowed only through the auditor, with both results
   reported.

**Logging proposal** (do not implement without the chair):

- New ledger event `catalogue_explore` with fields `phase` (2 or 3), `quadrant` ("explore"),
  `n_cells`, `n_views`, `grid` (path) and `grid_sha256`. Phase 2 logs one event: n_cells = 304,
  n_views = 5,092. Each phase-3 combination screen logs its own event with the views it was chosen from.
- `total_trials()` keeps summing only `registered` and `exploration`, so unrelated edge-lab work is not
  charged for catalogue cells. A new `catalogue_trials()` sums the `catalogue_explore` cells.
- Lineage field on `register()`: `lineage="catalogue"` when an idea came from catalogue output. Its
  deflated Sharpe then uses `total_trials() + catalogue_trials()`. Default: any card registered after
  phase 2 that tests a primitive phase 2 measured gets lineage "catalogue" unless the chair writes why
  not. This prevents the opposite failure, a catalogue idea re-entering the lab with a clean count.
- The sealed batch is registered normally with `register(n_cells = batch size, primaries = batch
  size)`; it counts in `total_trials()`.
- Until this exists, phase 2 must not use `log_exploration` silently: under the current code it would
  raise `total_trials()` from 71 to 375 for every later experiment.

### 5.3 Conditions a combination must meet on EXPLORE before it may be nominated

All required. A combination is at most two primitives plus at most one regime conditioner, built from
phase-2 cells.

1. **Mechanism first.** Counterparty, why it persists, predicted sign, horizon and regime written and
   committed before the combination's explore read. Combinations whose reason was written after the
   read are logged and cannot be nominated.
2. **Form.** Market-neutral (XS spread, pair, or market-hedged alpha vs MKT_A10) unless condition 7
   holds for the late-only directional read.
3. **Size vs cost.** Gross excess >= 3 x the form's round trip (39 bp single-leg; 78 bp two-leg or
   full-turnover long-short rebalance), and net > 0 after real funding at 1.5 x cost (reported at 2 x).
4. **Explore t >= 3.0** (above the luck ceiling of the effective phase-2 grid), hedged alpha t >= 2 where
   the form is directional, and panel null-shift p < 0.05 (every coin's signal shifted by the same
   offset; the auditor approves the implementation).
5. **Sign-stable across years**: predicted sign of gross excess in at least 4 of the 5 explore years
   (2020-2024) among years with at least 20 independent windows; at least 3 qualifying years.
6. **Plateau**: `measure.plateau_score` share_similar >= 0.5 over the published grid neighbours
   (adjacent lookbacks and adjacent horizons). A single-value card needs the same sign at both adjacent
   common horizons. Off-grid parameters cannot be nominated.
7. **Resolvable**: `power.n_required(0.5 x explore gross excess, explore window sd, t_bar=2.576,
   power=0.5)` <= the sealed windows available to its form (pooled for market-neutral; late only for
   directional). The 0.5 is the expected shrinkage of a selected effect: published anomalies lose about
   a quarter out of sample and about half after publication (McLean and Pontiff 2016; recalled, not
   re-fetched). For a daily XS spread this implies an explore t of about 4.4; for a raw directional
   1-day state, a gross edge of about 94 bp a day, which is why directional nominations are in practice
   excluded.
8. **Lookahead**: `measure.truncation_guard` returns [] for every signal, universe and regime series at
   cuts (0.5, 0.7, 0.9), the close-time assertion holds for any monthly or weekly series built from
   daily bars, and auditor stage A has signed off on the phase-3 engine.
9. **Distinct**: correlation of explore window returns with every other nominee below 0.5; nominees
   from different primitives or mechanisms.
10. **Tradable**: at least 80 % of explore trades in coins with a Bybit perp listed at the trade date
    (`bybit_listing.csv`), since that is the user's venue.

### 5.4 Pass bar on the sealed quadrants (all required together)

1. **n**: sealed independent windows >= the n_required computed at nomination.
2. **Primary**: date-clustered t of the drift-matched excess (clusters: pooled event panels W for a
   1-day hold, M for 2-14 days, Q beyond; rebalanced spreads with rows spaced at the hold W up to
   7 days, M for 14-30 days and for cohort composites; market-wide series W) (XS: `cross_sectional_ls` gross series; pairs: pair trade
   returns; hedged forms: the hedged alpha) >= 2.576, in the predicted direction. Market-neutral forms:
   pooled over late_A, early_B and late_B. Directional forms: late_A plus late_B only; early_B is a
   coin-robustness check, not evidence.
3. **Gross cost ratio >= 3** on the sealed read.
4. **Net > 0** after cost and real funding, at 1x and at 1.5x cost.
5. **Hedged alpha > 0 with t >= 2** vs MKT_A10 (for market-neutral forms, beta to MKT_A10 reported).
6. **Late era alone** (late_A plus late_B): predicted sign and net > 0. **early_B alone**: predicted sign.
   No t-bar on either (the late-only MDE is about 1.7x the pooled one), but a failure of either fails the
   verdict.
7. **At least 60 % of calendar years with 10 or more trades positive** (house rule).
8. **Null-shift p < 0.05** on the sealed read (panel shift).
9. **Deflated Sharpe > 0.95 with n_trials = 5**; DSR with `total_trials() + catalogue_trials()`
   reported, not a bar.
10. **Reported, never selected on**: per quadrant (late_A, early_B, late_B), per regime level, and at
    1x / 1.5x / 2x cost. No quadrant, coin, year or regime may be dropped; no rerun.
11. **Hurdle**: directional forms against the 14-15 %/yr pre-tax VGS/VAS hurdle (HANDOFF section 1);
    market-neutral forms by the sleeve's Sharpe, its return on gross capital, and its monthly
    correlation to MKT_A10 and to the VGS/VAS benchmark. Say which applies.
12. A pass goes to auditor stage B, then to the forward paper tracker at small size. Nobody calls it an
    edge before stage B. "Nearly passed" is a fail.

## 6. Task E: regimes (fixed now, lookahead-free, half-A data only)

**MKT_A10.** Each UTC day, the 10 U50A coins with the highest median quote volume over the 30 days
ending t-1 (volume > 0 on t-1, at least 90 live days). Daily return = equal-weight mean of their
close-to-close log returns (for trade windows, the equal-weight mean of their `trade_return(open, h)`).
At least 5 names required: first valid day 2020-04-18. The same MKT_A10, built from half A only, is used
for every coin in every quadrant; it is never rebuilt from half B. All regimes are evaluated at the close
of the signal bar t, before the fill at the open of t+1, and each is covered by the truncation guard.

| id | variable | definition | levels | explore distribution (days per level) |
|---|---|---|---|---|
| R1 | market trend | sign of the sum of MKT_A10 daily log returns over the 90 days ending t (90 valid days) | up / down | up share by year: 2021 0.78, 2022 0.06, 2023 0.40, 2024 0.50 (2020 mostly undefined); 58 switches in explore |
| R2 | market volatility | 30-day sd of MKT_A10 daily log returns (at least 25) x sqrt(365), as a percentile of its own values on days t-365..t-1 (at least 180) | low < 1/3, mid, high > 2/3 | high / low / mid: 2021 154/111/100, 2022 99/198/68, 2023 25/251/89, 2024 224/27/115 |
| R3 | funding | for each U50A coin with funding: mean f8 over all its settlements stamped in the 7 UTC days ending with day t (all strictly before the decision instant, 00:00 UTC of t+1; at least 5 days); cross-coin median (at least 5 coins) | short-crowded < 0.5 bp, neutral 0.5-1.5 bp, long-crowded > 1.5 bp per 8 h | explore quantiles of the median: 25 % 0.41, 50 % 0.90, 75 % 1.57 bp, so about 28 / 46 / 26 % of days; levels sit symmetrically around the exchange's 1 bp floor |
| R4 | liquidity | 30-day mean of the summed daily quote volume of the day's MKT_A10 constituents, logged, as a percentile of its own values on days t-365..t-1 (at least 180) | low, mid, high terciles | strongly persistent: 2021 mostly high (303 of 365), 2022-23 mostly low |
| R5 | calendar year | UTC year of t | 2020-2024 explore; 2025, 2026 sealed | |
| R6 (XS and carry only) | dispersion | cross-sectional sd of 7-day log returns across U50A coins (at least 10), as a percentile of its own values on days t-365..t-1 (at least 180) | low, mid, high terciles | balanced in 2023-24; 2022 mostly low |

Why these: R1 and R2 are the regime claims most cards make ("works in trends", "fails when vol is
low"); R3 is the positioning state behind carry and flush cards, with levels anchored on the
exchange's 1 bp floor rather than on percentiles, so a level means the same thing in every year; R4 is
the liquidity regime of the attention and volume cards; R5 catches era concentration (the repo's lesson:
the era is the variable); R6 is the opportunity set of any cross-sectional sort. The percentile regimes
(R2, R4, R6) are relative to the trailing year, so each level recurs in every year; R1 and R3 are
absolute and can be absent for a whole year (2022 has no up-trend and no long-crowded days). Funding
uses `f8` because it is a level comparison across 8 h, 4 h and 1 h coins; funding PAID uses `rate`.

## 7. Assumptions register

| assumption | value | where it matters | effect if wrong |
|---|---|---|---|
| sealed sd = explore sd | same | every sealed MDE | linear |
| real sort spread sd / placebo spread sd | 1.5 | XS and carry MDEs | linear |
| half-A vs half-B same-date spread correlation | 0.5 | late-era XS MDE | small (sqrt((1+c)/2)) |
| residual same-date correlation after the market hedge | 0.05 | hedged TS MDE | 0.10 raises the 1-day sign-state MDE by about 30 % |
| extreme states fire independently across coins | 5 % of coin-days | extreme-state MDE | clustered states have fewer windows: worse |
| early_B listing pace = explore's | same windows | early_B part of pooled reads | small; half-A and half-B live-coin counts match within about 10 % at every half-year |
| hourly sd = daily / sqrt(24) | 92 bp | hour-of-day MDE | intraday vol pattern ignored |
| T2 OI-flush dates at full universe | 50 explore, 20 late | FLOW MDE | H010 measured 25 / 9 on 8 coins |
| selection shrinkage | 0.5 | nomination rule 7 | McLean and Pontiff, recalled |
| A/B market path correlation | 0.94 (sub-half proxy) | excluding early_B for directional forms | already near 1 |

