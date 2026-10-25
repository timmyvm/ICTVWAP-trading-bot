# Catalogue family: breakout, range and volatility

Family code `BRK`. Compiled 2026-10-10. Outcome-blind: no repo result, ledger, verdict or data
cache was consulted. Every number under "Published claim" is the source's own figure for its own
market and era, not ours. Arithmetic in "Cost-floor note" and "Event rate" uses only the rule, the
source's published numbers and stated illustrative inputs (marked "at X%").

Fidelity policy in this file. **A**: primary source read in full, and it states the rule parameters.
**B**: rules come from a secondary description, the primary was read only in part, or one leg of
the rule (usually the exit) is not specified by the source. **C**: no primary source found or read
(folklore), or the rule is not mechanizable. "Read: full" means the full text of the relevant
sections was read; "abstract" or "summary" means only that. "Recalled, not re-fetched" marks
anything taken from memory of a book or paper that was not opened during this pass.

Cost reference (CATALOGUE.md §7): a perp round trip is 13 bp. Several sources here assume costs of
0.1-2 bp a side; each card converts that to the same units.

Coverage note: the web-search allowance ran out before dedicated searches for academic
inside-bar and FX session-breakout studies; for those two seeds "no primary source found" means
"none found in this pass", not "none exists".

---

### S-BRK-01 Crabel open ± stretch breakout after a narrow-range period
- **Fidelity.** B. Crabel's book is out of print and was not read; the rules come from a secondary implementation.
- **Sources.**
  - T. Crabel, *Day Trading with Short Term Price Patterns and Opening Range Breakout*, Traders Press, 1990 (not read; recalled, not re-fetched).
  - Oxford Capital Strategies, "Narrow Range" strategy page, https://oxfordstrat.com/trading-strategies/narrow-range/ (read: full).
  - Holmberg, Lönnbark and Lundström, "Assessing the profitability of intraday opening range breakout strategies", *Finance Research Letters* 10(1), 2013, https://ideas.repec.org/a/eee/finlet/v10y2013i1p27-33.html (read: abstract).
- **Rule.**
  - Setup: the high-low range of the last N days is the narrowest of any N-day window within the look-back (secondary tests N = 2-19, look-back 20-50).
  - Next day: buy stop at Open + Stretch and sell stop at Open − Stretch. Stretch = 2 × 10-day SMA of Noise, Noise = min(High − Open, Open − Low). The first stop hit is the position and the other becomes its protective stop; both hit on one day counts as one loss.
  - Exit: close of the 10th daily bar, the opposite stretch stop, or a 6 × ATR(20) stop. Sizing 1% fixed-fractional.
  - Data: daily OHLC. Secondary universe: 42 futures, 1980-2013.
- **Primitive vs wrapper.** Primary P2 (contraction precedes expansion); secondary P1 (direction = the side on which price leaves the open by more than normal noise). Wrapper: NR-N filter, stretch multiple, 10-bar time exit, 6 ATR stop.
- **Claimed mechanism.** Quiet periods store up a move, and a move away from the open larger than ordinary noise marks a trend day. No counterparty argument is offered.
- **Published claim.** Secondary shows results only as charts (gross, and with $50 a round turn) and rates the strategy "C" on its own A-D scale. Holmberg et al. (abstract, crude-oil futures keyword): returns significantly above zero and a success rate above a fair game; the abstract gives no numbers.
- **Decay and crowding.** Nothing quantified in what was read.
- **Cost-floor note.** Holding up to 10 days with a 6 ATR stop, so 13 bp is small next to the risk unit. The costly case is the whipsaw day: both stops hit means a loss of 2 × Stretch plus two round trips.
- **Event rate (estimate).** If daily ranges were exchangeable an NR7 day occurs 1 day in 7 (~52 a year on 365-day crypto, ~36 on 250-day futures), NR4 1 in 4 (~91). Quiet days cluster across coins, so date-independent events ≈ the single-market count.
- **Applies to / testable here.** Futures (source). Y on perps with daily bars anchored at 00:00 UTC, but a 24/7 "open" carries no overnight information.
- **Regime hypothesis.** Works where a session open releases stored information and quiet spells end in trend days; fails in 24/7 markets with no information-laden open and in low-vol chop where the stretch is crossed both ways.
- **Overlaps.** S-BRK-02 (same contraction filter, bar-extreme entry), S-BRK-06 (open + fraction of range), S-BRK-03/04.

### S-BRK-02 NR4 / NR7 / inside-bar breakout
- **Fidelity.** B. Secondary description only; the primaries (Crabel; Raschke and Connors) were not read. Holding horizon not specified beyond stop-and-reverse.
- **Sources.**
  - LuxAlgo, "NR4/NR7 Narrow-range Bars" concept page, https://www.luxalgo.com/library/concept/nr4-nr7-narrow-range-bars.md (read: full). Attributes the pattern to Crabel (1990) and says Crabel later withdrew the book.
  - L. Raschke and L. Connors, *Street Smarts*, M. Gordon Publishing, 1995, "ID/NR4" setup (recalled, not re-fetched).
  - Plain inside-bar breakout: no primary source found (folklore).
- **Rule.**
  - Setup: NR4 = the bar's high-low is the narrowest of the last 4 bars; NR7 = of the last 7; ID/NR4 = an NR4 bar that is also inside the prior bar (lower high, higher low). Inside-bar variant: the inside bar alone.
  - Entry: buy stop just above the setup bar's high and sell stop just below its low; take whichever triggers first.
  - Exit: the opposite extreme as stop, or as stop-and-reverse. Optional: skip if the bar's range is below a fraction of ATR; take only the side of a higher-timeframe trend.
  - Data: OHLC on any bar size; the source era used daily futures.
- **Primitive vs wrapper.** Primary P2; secondary P8 (bar extremes used as levels). Wrapper: stop-and-reverse, ATR floor, trend filter.
- **Claimed mechanism.** Expansion follows compression more often than chance. The source itself says break direction is effectively a coin flip and first breaks often fail. No counterparty named.
- **Published claim.** No numbers read. Secondary paraphrases Crabel's tables as "meaningful but modest edges" for his markets and era.
- **Decay and crowding.** Secondary: the effect has been "re-confirmed only loosely". Nothing quantified.
- **Cost-floor note.** The risk unit R is the setup bar's own range, chosen as the smallest of 4-7 bars, so cost = 13 bp / range: a 26 bp bar costs 0.5 R per round trip. On intraday bars this is a stop below the cost floor by construction; only daily bars escape it.
- **Event rate (estimate).** NR4 about 1 bar in 4, NR7 about 1 in 7 (exchangeability arithmetic). Daily: ~50-90 a year per market, date-clustered across coins.
- **Applies to / testable here.** Futures and stocks (source). Y (klines at any timeframe).
- **Regime hypothesis.** As a P2 state it should predict a larger next-bar range in every regime; direction adds edge only with a trend filter in trending regimes; fails in dead tape (hence the ATR floor).
- **Overlaps.** S-BRK-01 (same state, open-anchored entry), S-BRK-08 (the same contraction measured with bands).

### S-BRK-03 Zarattini-Aziz 5-minute opening range breakout on QQQ
- **Fidelity.** B. SSRN abstract read; the rules come from secondary summaries.
- **Sources.**
  - C. Zarattini and A. Aziz, "Can Day Trading Really Be Profitable?", SSRN 4416622, Apr 2023 (rev. Sep 2025), https://papers.ssrn.com/abstract=4416622 (read: abstract).
  - CXO Advisory summary, https://www.cxoadvisory.com/technical-trading/day-trading-with-an-opening-range-breakout-strategy (read: rules; results paywalled). Retail Traders Repository summary, https://retailtradersrepository.substack.com/p/trading-research-paper-can-day-trading-really-be-profitable (read).
  - T.-P. Krueger, "The opening-range breakout paper, replicated on five indices: gross reproduced, net zero", MQL5 blog, Sep 2026, https://www.mql5.com/en/blogs/post/776235 (read: full).
- **Rule.**
  - Signal: the first 5-minute bar (09:30-09:35 ET). Up bar → long; down bar → short; doji (open = close) → no trade.
  - Entry at the open of the second 5-minute bar. Stop at the first bar's low (long) or high (short). Target 10 × |entry − stop|; otherwise exit at 16:00.
  - Sizing: risk 1% of equity per trade, max 4× leverage. Costs: $0.0005 a share commission, no spread or slippage.
  - Variant (TQQQ): stop = 5% of the 14-day ATR, no target, exit at the close.
  - Data: QQQ and TQQQ intraday, 2016-01 to 2023-02.
- **Primitive vs wrapper.** Primary P1 (the sign of the first 5 minutes continues to the close); secondary P5 (the cash-open clock). Wrapper: one-bar stop, 10R target, end-of-day exit, leverage.
- **Claimed mechanism.** The abstract offers none beyond "profitable with proper leverage". The companion paper (S-BRK-04) argues an opening supply-demand imbalance persists through the session.
- **Published claim.** Source, QQQ 2016-2023: annualized alpha 33% net of commissions; TQQQ version 1,484% total vs 169% for QQQ. Secondary: average +0.18 R per trade; the ATR-stop variant reports "93% annualized alpha" with no slippage modelled.
- **Decay and crowding.** Krueger's replication on index CFDs (NQ, SPX, Dow, DAX, FTSE; 2015-2026): gross +0.04 to +0.15 R per trade; net of spread and slippage −0.08 to +0.00 R (t from −1.9 to 0.0).
- **Cost-floor note.** R = the first bar's range, so cost = 13 bp / that range: a 20 bp opening bar puts 0.65 R of cost on every trade, against a published mean of +0.18 R. The ATR variant's R is 0.05 × ATR: at a 3% daily ATR, R = 15 bp and cost ≈ 0.87 R. The source's commission is ~0.05 bp a side at a $100 QQQ.
- **Event rate (estimate).** At most one a trading day minus dojis: ~250 a year on one index, each day independent.
- **Applies to / testable here.** US index ETFs. Partial (cached NQ intraday). Y on perps only with an arbitrary anchor (00:00 UTC or the US cash open), which changes the mechanism.
- **Regime hypothesis.** Works on days whose open carries overnight news and in high-vol trending regimes; fails in quiet mean-reverting sessions and whenever the opening bar is narrow relative to cost.
- **Overlaps.** S-BRK-04 (same entry plus volume selection), S-BRK-05, S-BRK-13 (gap-and-go).

### S-BRK-04 Opening range breakout on "Stocks in Play" (relative-volume filter)
- **Fidelity.** A.
- **Sources.** C. Zarattini, A. Barbon and A. Aziz, "A Profitable Day Trading Strategy For The U.S. Equity Market", SSRN / Univ. St. Gallen working paper, 16 Feb 2024, https://www.alexandria.unisg.ch/server/api/core/bitstreams/3c2989c4-688d-4d78-8a71-f02690990d51/content (read: full).
- **Rule.**
  - Daily universe: US stocks with open > $5, 14-day average volume ≥ 1M shares, 14-day ATR > $0.50, and opening-range Relative Volume (first-5-minute volume ÷ its 14-day average for the same window) ≥ 100%. Trade the top 20 by Relative Volume.
  - Direction: first 5-minute bar up → long only; down → short only; doji → none.
  - Entry: stop order at the first bar's high (long) or low (short). Stop: 10% of the 14-day ATR from entry. No target; exit 16:00 ET.
  - Sizing: risk 1% of equity per trade, max 4× leverage. Costs: $0.0035 a share; no slippage or borrow cost.
  - Data: intraday bars, ~7,000 stocks including delisted, 2016-2023. 15/30/60-minute ranges also tested.
- **Primitive vs wrapper.** Primary P1 (early-session direction continues); secondary P7 (abnormal opening volume) and P5. Wrapper: 0.1 ATR stop, end-of-day exit, top-20 cap.
- **Claimed mechanism.** On catalyst days (earnings, M&A, FDA) an institutional supply-demand imbalance at the open persists through the session; retail-favourite names move harder on sentiment. Other side: intraday liquidity providers and faders.
- **Published claim.** Source, US stocks 2016-2023, net of commission: with the RV filter 1,637% total, IRR 41.6%, Sharpe 2.81, max DD 12%, beta 0.00; without it 29%, Sharpe 0.48. Trades with RV < 100% averaged −0.02 R; RV > 100% +0.08 R; RV > 30× +0.38 R. 5-minute best; 30-minute Sharpe 0.21.
- **Decay and crowding.** No out-of-sample test, sensitivity analysis or subperiod split in the paper. Authors are practitioners with trading-education ties.
- **Cost-floor note.** R = 0.1 × ATR, so cost = 13 bp / (0.1 × ATR). At a 4% ATR, R = 40 bp and cost = 0.33 R, above the +0.08 R mean of RV > 100% trades; 13 bp drops below 0.08 R only at ATR ≥ ~16%, and below the RV > 30× mean (0.38 R) at ATR ≥ ~3.4%. The source's commission is ~1.75 bp a side at a $20 stock.
- **Event rate (estimate).** Up to 20 trades a day but one date cluster: ~250 date-independent days a year.
- **Applies to / testable here.** US equities: N (needs an intraday cross-section of stocks). Y for a crypto analogue (rank perps by relative volume in a fixed opening window), though scheduled catalysts are mostly absent.
- **Regime hypothesis.** Works on news days with abnormal participation; fails on no-news days (the source's RV < 1 trades were negative) and in markets without scheduled catalysts at a session open.
- **Overlaps.** S-BRK-03 (same entry), S-BRK-13 (gap days are often the high-RV days).

### S-BRK-05 Noise-area intraday momentum (SPY)
- **Fidelity.** A.
- **Sources.** C. Zarattini, A. Aziz and A. Barbon, "Beat the Market: An Effective Intraday Momentum Strategy for S&P500 ETF (SPY)", Swiss Finance Institute RP 24-97, May 2024 (rev. Feb 2025), https://alexandria.unisg.ch/server/api/core/bitstreams/a99aba00-f967-49b3-aceb-f544dc386e0b/content (read: full).
- **Rule.**
  - σ(t) for each time of day = mean over the prior 14 days of |price at t ÷ that day's 09:30 open − 1|.
  - Upper = max(open, prior 16:00 close) × (1 + σ(t)); Lower = min(open, prior close) × (1 − σ(t)). Volatility multiplier 1.
  - Check only at HH:00 and HH:30: long if price > Upper, short if price < Lower.
  - Exit: trailing stop at max(Upper, VWAP) for longs and min(Lower, VWAP) for shorts, checked on the same half-hours; crossing the opposite band reverses; flat at 16:00.
  - Sizing: shares = AUM × min(4, 2% ÷ 14-day daily σ of SPY) ÷ open. Costs $0.0035 a share commission + $0.001 slippage. Data: SPY 1-minute, 2007-2024.
- **Primitive vs wrapper.** Primary P1 (continuation once a move exceeds its time-of-day norm); secondary P2 (band in vol units) and P5 (time-of-day σ, half-hour clock). Wrapper: VWAP trail, reversal, vol-targeted size.
- **Claimed mechanism.** Persistent supply-demand imbalances and slow incorporation of news (citing Gao et al. and Baltussen et al.). Dealer gamma hedging is offered as an amplifier, proxied by 5-day RSI (beta −3.25, p = 0.001); gamma itself is not measured.
- **Published claim.** Source, SPY 2007-2024, net: 19.6%/yr, vol 14.3%, Sharpe 1.33, max DD 25%, vs SPY 7.2%/yr, Sharpe 0.45. Base model without VWAP trail or sizing: Sharpe 0.61. With an I-Star impact model: Sharpe 1.17.
- **Decay and crowding.** The paper cites Rosa (2022) finding intraday predictability declined after 2013. The authors report 2024 at +32.2% and argue decay risk is small.
- **Cost-floor note.** The source's cost is $0.0045 a share a side, ~0.1-0.2 bp at SPY $200-500. 13 bp is ~30-70× its round trip, and each reversal adds another.
- **Event rate (estimate).** At most one entry a day plus reversals: ≤ ~250 date-independent days a year (the share of days with a breach is not stated).
- **Applies to / testable here.** SPY (source). Partial (cached NQ 1m). Y on perps with a chosen anchor, but "prior close" and the cash open are undefined in 24/7 trading.
- **Regime hypothesis.** Works in high-vol trending regimes and when dealers are short gamma; fails when dealers are long gamma (the source's RSI result) and in low-vol ranges.
- **Overlaps.** S-BRK-03/04 (open-anchored continuation), S-BRK-06 (open ± a range fraction), S-BRK-14 (the sizing step).

### S-BRK-06 Larry Williams volatility breakout (open + k × prior range)
- **Fidelity.** C. The original book was not read, and the only rule set read states its formula ambiguously.
- **Sources.**
  - L. Williams, *Long-Term Secrets to Short-Term Trading*, Wiley, 1999 (recalled, not re-fetched).
  - WH SelfInvest, "Larry Williams Volatility Break-out" free strategy page, https://whselfinvest.com/en-be/trading-platform/free-trading-strategies/tradingsystem/56-volatility-break-out-larry-williams-free (read: full; vendor).
  - S. Hong, "Comparative Study of Automatic Trading and Buy-and-Hold in the S&P 500 Index Using a Volatility Breakout Strategy", *J. of Internet of Things and Convergence* 9(6), 2023, https://koreascience.or.kr/article/JAKO202301043221303.pub?lang=en (read: abstract).
- **Rule.**
  - Vendor version: levels = session open ± 0.25 × previous day's high-low (wording ambiguous); 5-minute bars; long above the upper level, short below the lower; usually one signal a day.
  - Vendor exit: target and stop each 2 × the breakout distance from entry; flat at 21:59 if neither is hit.
  - Original (recalled, not re-fetched): buy at the open + a percentage of the prior day's (or a multi-day) range; exit on a protective stop or at the first profitable opening.
  - Retail crypto variant (recalled, not re-fetched; no primary found): long at open + k × prior range with k ≈ 0.5, exit at the next daily open.
- **Primitive vs wrapper.** Primary P1 (a move of k ranges from the open continues); secondary P2 (range-scaled trigger) and P5 (daily open anchor). Wrapper: k, exits, time stop.
- **Claimed mechanism.** A large move from the open shows the day's direction. The vendor says it underperforms in sideways or low-vol markets. No counterparty argument.
- **Published claim.** Vendor: profits "are variable but none are negative" (DAX, Dow, Nasdaq, S&P 500, CAC 40, Bund; figures only as images). Hong (abstract): "slightly higher" return than buy-and-hold on the S&P 500; k not reported.
- **Decay and crowding.** Nothing quantified.
- **Cost-floor note.** Daily-hold variant: one round trip against a full day's move. Vendor variant: R = 0.5 × prior range; at a 2% prior range, R = 100 bp and cost = 0.13 R.
- **Event rate (estimate).** At most one a day per market (~365 a year on crypto), heavily date-clustered across coins.
- **Applies to / testable here.** Index futures, FX, stocks (sources). Y (1m klines, open at 00:00 UTC).
- **Regime hypothesis.** Works in trending, expanding-vol regimes; fails in range-bound chop.
- **Overlaps.** S-BRK-01 (Crabel's stretch: the same idea with noise in place of range), S-BRK-05, S-BRK-07.

### S-BRK-07 London breakout of the Asian range (FX)
- **Fidelity.** C. No primary source found; one secondary rule set read.
- **Sources.**
  - Backtrex, "Does the London breakout strategy work on EUR/USD?", https://backtrex.com/en/backtests/london-breakout-eur-usd (read: full; marketing page; rules attributed to Quantified Strategies, not read).
  - K. Sakamoto, "Why the Same Strategy Wins in London and Dies in Tokyo", MQL5 blog, Aug 2026, https://www.mql5.com/en/blogs/post/774527 (read: full; promotional, qualitative only).
- **Rule (secondary version).**
  - Asian range = high and low of 00:00-06:00 UTC, EUR/USD 1-hour bars.
  - Long when an hourly close crosses above the Asian high between 07:00 and 10:00 UTC; short on a close below the Asian low.
  - Stop 35 pips, target 70 pips; no time exit stated.
- **Primitive vs wrapper.** Primary P5 (London-open order flow); secondary P1 and P2. Wrapper: fixed-pip stop and target, 07-10 UTC window.
- **Claimed mechanism.** Tokyo is range-bound; London's first two hours bring the volume that breaks ranges and starts trends. Nothing on who is on the other side.
- **Published claim.** Secondary's own backtest, EUR/USD 2016-10 to 2026-10, 0.02% a side: 1,230 trades, win rate 36.3%, profit factor 0.87, total −28%.
- **Decay and crowding.** Nothing quantified.
- **Cost-floor note.** 35 pips at EUR/USD 1.10 is ~32 bp, so 13 bp ≈ 0.4 R. The backtest charged ~4 bp a round trip.
- **Event rate (estimate).** At most one a weekday per pair (~260 a year); USD pairs cluster.
- **Applies to / testable here.** FX. Partial (cached FX intraday). Y as a crypto adaptation (Asian-hours range broken in European hours), with a weaker mechanism.
- **Regime hypothesis.** Works when the European open brings new orders (data releases, rebalancing); fails in quiet weeks and when the Asian session has already trended.
- **Overlaps.** S-BRK-03 (a session ORB with a longer range), S-BRK-06.

### S-BRK-08 Bollinger squeeze / TTM Squeeze
- **Fidelity.** B. Bollinger's manual is primary for the entry; TTM rules are secondary; neither source specifies an exit.
- **Sources.**
  - J. Bollinger, *Bollinger Bands Volatility Breakout (Method I) Manual*, 2021, https://www.bollingerbands.com/_files/ugd/58be43_f5e967053af44fa083340cacfc5e6226.pdf (read: full).
  - LuxAlgo, "TTM Squeeze" concept page, https://www.luxalgo.com/library/concept/ttm-squeeze.md (read: full). J. Carter, *Mastering the Trade*, McGraw-Hill, 2005 (recalled, not re-fetched).
- **Rule.**
  - Bollinger: BandWidth = (upper − lower) ÷ middle, bands = 20-period SMA ± 2 sd. Squeeze = BandWidth at a 125-period low (3% buffer). Long alert on a break above the upper band within 5 bars after a squeeze; short on a break below the lower band. Exit: not specified.
  - TTM: squeeze ON while BB(20, 2) lies inside Keltner (20 SMA ± 1.5 × ATR20). Fires on the first OFF bar; direction = sign of momentum = 20-bar linear regression of close − ((HH20 + LL20)/2 + SMA20)/2. Exit: no hard rule (histogram fading toward zero).
  - Data: OHLC, any bar size.
- **Primitive vs wrapper.** Primary P2 (compression precedes expansion); secondary P1 (direction from band side or momentum sign). Wrapper: band break or momentum sign, buffers, exits.
- **Claimed mechanism.** Low volatility is followed by high volatility. Neither source names a counterparty.
- **Published claim.** None. Bollinger reports "most success" with brief squeezes that break quickly, unquantified; the TTM secondary says fires can fail and squeeze duration says nothing about move size.
- **Decay and crowding.** Nothing quantified.
- **Cost-floor note.** A 125-period BandWidth low is the minimum-vol state by construction, so an intraday stop inside the bands compresses R toward cost. Daily bars with multi-day holds keep 13 bp a small share of the move.
- **Event rate (estimate).** 125-bar BandWidth lows are rare: 2-6 a year per market on daily bars; quiet regimes cluster across coins.
- **Applies to / testable here.** Any market. Y.
- **Regime hypothesis.** The P2 part should show in every regime as larger forward |return|; a sign edge only in trending regimes; fails when the squeeze resolves as a false break in both directions.
- **Overlaps.** S-BRK-01/02 (same contraction state), S-BRK-06.

### S-BRK-09 Turtle Donchian channel breakout (20/55-day)
- **Fidelity.** B. Secondary implementation read; the original rules document was not re-fetched.
- **Sources.**
  - C. Faith, *The Original Turtle Trading Rules*, free document, c. 2003, and *Way of the Turtle*, McGraw-Hill, 2007 (both recalled, not re-fetched).
  - T. M. Hector, "Automating Classic Market Methods in MQL5 (Part 5): The Original Turtle Trading Rules", MQL5 article, Aug 2026, https://www.mql5.com/en/articles/23448 (read: full).
- **Rule.**
  - N = 20-day Wilder average true range. Unit sized so a 2N adverse move ≈ 1% of equity (secondary); the original, recalled: a 1N move = 1% of equity.
  - System 1: enter on a break of the prior 20-day high (long) or low (short); skip if the last System 1 trade in that direction won; exit on a 10-day opposite breakout.
  - System 2: 55-day breakout entry, every signal taken; exit on a 20-day opposite breakout.
  - Add a unit every N/2 in favour, max 4 units; shared stop 2N from the latest entry. No target.
  - Data: daily OHLC, liquid futures.
- **Primitive vs wrapper.** Primary P1 (time-series trend); secondary P2 (N sizing). Wrapper: skip-after-winner, pyramiding, 2N stop, channel exits.
- **Claimed mechanism.** Trends run further than prices discount (recalled framing; not in the pages read). Neither source read names the other side.
- **Published claim.** No performance number read.
- **Decay and crowding.** Trend-following crowding is widely discussed; nothing quantified in what was read.
- **Cost-floor note.** Stop 2N: at N = 3% the stop is 600 bp, so 13 bp ≈ 0.02 R. Not cost-bound; funding over multi-week perp holds matters more.
- **Event rate (estimate).** 3-8 55-day breakouts per market a year; crypto trends are market-wide, so ~5-15 date-independent episodes a year.
- **Applies to / testable here.** Futures (source). Y (daily klines plus funding).
- **Regime hypothesis.** Works in persistent trend regimes; bleeds in choppy mean-reverting markets; the skip rule adds path dependence.
- **Overlaps.** S-BRK-10, S-BRK-11, S-BRK-12; the trend family.

### S-BRK-10 Channel-breakout and support/resistance rules in crypto
- **Fidelity.** A. Full paper read; it tests a parameter grid, not one rule.
- **Sources.**
  - R. Hudson and A. Urquhart, "Technical trading and cryptocurrencies", *Annals of Operations Research*, 2019, doi 10.1007/s10479-019-03357-1, https://hull-repository.worktribe.com/OutputFile/2639834 (read: full).
  - W. Brock, J. Lakonishok and B. LeBaron, "Simple Technical Trading Rules and the Stochastic Properties of Stock Returns", *J. of Finance* 47(5), 1992, https://ideas.repec.org/a/bla/jfinan/v47y1992i5p1731-64.html (read: abstract).
- **Rule.**
  - Rule classes after Hsu et al. (2016). Channel breakout (CB): lookback j = 2-200 days, breakout threshold x = 0-5%, channel width c = 0.01-0.5, d = 2-5 consecutive days beyond the band; CB2 holds k = 3 or 5 days (4,536 variants). Construction (recalled, not re-fetched, from Sullivan-Timmermann-White): a channel exists when the j-day high is within c of the j-day low; buy when the close exceeds the channel by x.
  - Support/resistance (SR): resistance = highest price of the previous j; support = lowest close of the previous j; threshold x, d days, optional hold k (945 variants).
  - Data: daily; BTC (CoinDesk from 2010, Bitstamp from 2012), LTC, XRP, ETH to end-2017; out-of-sample H1 2018.
- **Primitive vs wrapper.** Primary P1; secondary P8 (prior high/low as level). Wrapper: x, d, k, c.
- **Claimed mechanism.** None specific; cites the literature on declining rule performance (Menkhoff 2007; McLean and Pontiff 2016).
- **Published claim.** Source, zero cost: CB average 7.9%/yr (Bitstamp) to 16.0%/yr (ETH), significant at 1%; breakeven costs 30-144 bp. SR: 2-5%/yr, breakeven 8-16 bp. BLL (abstract, DJIA 1897-1986): buy signals beat sell signals; returns after sell signals negative.
- **Decay and crowding.** Best in-sample CB2 rules out of sample (H1 2018): BTC −0.10% (CoinDesk) and −0.91% (Bitstamp) annualized; LTC +7.75%. Authors: no out-of-sample predictability for Bitcoin.
- **Cost-floor note.** 13 bp is below the source's CB breakevens but inside the SR range (8-16 bp), so SR variants are cost-bound by the source's own numbers.
- **Event rate (estimate).** 10-30 signals per coin a year at mid-length j; date-clustered across coins.
- **Applies to / testable here.** Crypto spot (source). Y.
- **Regime hypothesis.** Works in early, trending, less efficient crypto eras; fails as an asset matures (the source's BTC out-of-sample) and in ranges.
- **Overlaps.** S-BRK-09, S-BRK-11.

### S-BRK-11 Donchian-ensemble trend following in crypto ("Catching Crypto Trends")
- **Fidelity.** C. Only abstract-level pages read; lookbacks, exits and sizing are not specified in what was read.
- **Sources.** C. Zarattini, A. Pagani and A. Barbon, "Catching Crypto Trends; A Tactical Approach for Bitcoin and Altcoins", Swiss Finance Institute RP 25-80, 2025, SSRN 5209907, https://ideas.repec.org/p/chf/rpseri/rp2580.html and https://concretumgroup.com/catching-crypto-trends-a-tactical-approach-for-bitcoin-and-altcoins/ (read: abstract and summary).
- **Rule.**
  - Several Donchian-channel trend models with different lookbacks combined into one signal; volatility-based position sizing.
  - Rotational portfolio of the 20 most liquid coins, from a survivorship-bias-free universe since 2015; a portfolio technique to cut trading costs.
  - Lookbacks, entry/exit, long/short, vol target and rebalance frequency: not specified.
- **Primitive vs wrapper.** Primary P1; secondary P2 (vol sizing) and P3 (rotation among the top 20). Wrapper: ensemble, sizing, cost technique.
- **Claimed mechanism.** Extends trend following from traditional assets to crypto; no mechanism stated in the pages read.
- **Published claim.** Source: net Sharpe above 1.5; annualized alpha 10.8% vs Bitcoin; return profile differs from traditional trend portfolios.
- **Decay and crowding.** Not discussed in what was read.
- **Cost-floor note.** Daily signals with multi-week holds; turnover depends on the unread ensemble rule.
- **Event rate (estimate).** 3-10 market-wide trend episodes a year.
- **Applies to / testable here.** Crypto. Y (daily klines; survivorship needs delisted coins in the universe).
- **Regime hypothesis.** Works in strong, persistent crypto trends; fails in multi-month ranges.
- **Overlaps.** S-BRK-09, S-BRK-10, S-BRK-14 (sizing).

### S-BRK-12 Darvas box
- **Fidelity.** C, not mechanizable as published: the box confirmation length, volume test and stock selection are discretionary.
- **Sources.**
  - N. Darvas, *How I Made $2,000,000 in the Stock Market*, 1960 (recalled, not re-fetched).
  - C. Mitchell, "The technical foundations of Nicolas Darvas's trading strategy", Trade That Swing, https://tradethatswing.com/the-technical-foundations-of-nicolas-darvass-trading-strategy/ (read: full).
  - T. M. Hector, "Automating Classic Market Methods in MQL5 (Part 7): The Nicolas Darvas Box System", Sep 2026, https://www.mql5.com/en/articles/24111 (read: full).
- **Rule.**
  - Selection (secondary): stocks at new 52-week highs with strong relative strength, volume on advances and a strong industry group.
  - Box: after a new high, that high is not exceeded for "several days" (secondary). One implementation: a 50-bar new high held for 3 bars, bottom = lowest low during formation, height ≥ 0.5 ATR.
  - Entry: close above the box top on expanding volume (implementation: breakout volume ≥ 1.3 × box average). Stop just below the box bottom; raise it to each new box's bottom; add units on new box breakouts.
- **Primitive vs wrapper.** Primary P1 (new-high continuation); secondary P3 (strength selection) and P7 (volume). Wrapper: box geometry, stop ladder.
- **Claimed mechanism.** Stocks making new highs on volume keep rising. The source is anecdote; no counterparty.
- **Published claim.** The book is a personal account. Neither secondary reports figures; the implementation projects 10-20 signals a year on EUR/USD daily, a projection, not a result.
- **Decay and crowding.** Nothing quantified.
- **Cost-floor note.** Daily bars, holds of weeks, stop at the box bottom several % away: not cost-bound.
- **Event rate (estimate).** A few per stock a year; clustered in bull markets.
- **Applies to / testable here.** US stocks (source). Y as an adaptation on perps (daily klines and volume).
- **Regime hypothesis.** Works in broad bull markets with clear leaders; fails in bear and choppy markets.
- **Overlaps.** S-BRK-09 (N-day-high breakout); the 52-week-high momentum literature.

### S-BRK-13 Opening gaps: fade (FX) and continuation (US indices)
- **Fidelity.** A for the FX fade. The continuation variant is C (abstract only; no rule given).
- **Sources.**
  - G. M. Caporale and A. Plastun, "Price gaps: Another market anomaly?", *Investment Analysts Journal* 46(4), 2017, https://bura.brunel.ac.uk/bitstream/2438/25828/5/FullText.pdf (read: full).
  - A. Plastun, X. Sibande, R. Gupta and M. E. Wohar, "Price gap anomaly in the US stock market: The whole story", *North American J. of Economics and Finance* 52, 2020, https://ideas.repec.org/p/pre/wpaper/201963.html (read: abstract).
- **Rule.**
  - Gap = today's open − yesterday's close, daily data.
  - Fade (FX): if the open is above the prior close by ≥ 0.1% (EUR/USD) or ≥ 0.05% (GBP/USD), thresholds optimized over 0.05-1%, sell at the open and close at the end of the day.
  - Continuation (US indices): prices tend to move in the gap's direction on the gap day; no rule given in the abstract.
- **Primitive vs wrapper.** Primary P1 over one day (reversal in FX, continuation in indices); secondary P5 (session boundary). Wrapper: gap threshold, same-day exit.
- **Claimed mechanism.** None beyond "anomaly". In 24-hour FX a daily gap is mostly the weekend gap or a vendor day-boundary effect.
- **Published claim.** Source, 2000-2015: EUR/USD 148 trades, 63.5% winners, +18 points a trade; GBP/USD 221 trades, 60%, +22 points; z = 2.43 and 3.15; losing years 3/16 and 2/16. Other markets consistent with efficiency; Dow up after positive gaps on 80% of first days (not traded); up to 80% of gaps unfilled after five days. Plastun et al. (1928-2018): gap-day momentum, temporary; gap-fill rejected.
- **Decay and crowding.** Plastun et al. call the momentum temporary; no decay series read.
- **Cost-floor note.** If a "point" is a pip, 18 pips ≈ 16 bp at EUR/USD 1.10, about one 13 bp round trip; and the threshold was chosen in sample.
- **Event rate (estimate).** From the source: 148/16 ≈ 9 a year (EUR/USD), 221/16 ≈ 14 a year (GBP/USD).
- **Applies to / testable here.** FX, US indices, commodities, stocks. Partial (cached FX and NQ intraday). N on perps: no session gap in 24/7 trading; CME bitcoin-futures gaps would need CME data.
- **Regime hypothesis.** The fade works when gaps reflect thin weekend quotes that revert as liquidity returns; continuation works when the gap carries real news (earnings, macro).
- **Overlaps.** S-BRK-03/04 (gap days drive opening-range breaks).

### S-BRK-14 Volatility-managed exposure (vol scaling and vol targeting)
- **Fidelity.** A. Moreira-Muir and Harvey et al. read in full; Cederburg et al. and Barroso-Santa-Clara abstracts only.
- **Sources.**
  - A. Moreira and T. Muir, "Volatility-Managed Portfolios", *J. of Finance* 72(4), 2017; NBER WP 22208, https://www.nber.org/papers/w22208.pdf (read: full).
  - C. Harvey, E. Hoyle, R. Korgaonkar, S. Rattray, M. Sargaison and O. Van Hemert, "The Impact of Volatility Targeting", *J. of Portfolio Management* 45(1), 2018, https://people.duke.edu/~charvey/Research/Published_Papers/P135_The_impact_of.pdf (read: full).
  - S. Cederburg, M. O'Doherty, F. Wang and X. Yan, "On the performance of volatility-managed portfolios", *JFE* 138(1), 2020, https://ideas.repec.org/a/eee/jfinec/v138y2020i1p95-117.html (read: abstract). P. Barroso and P. Santa-Clara, "Momentum has its moments", *JFE* 116(1), 2015, https://ciencia.ucp.pt/en/publications/momentum-has-its-moments/ (read: abstract).
- **Rule.**
  - Moreira-Muir: weight = c ÷ σ²(t), σ² = realized variance of daily returns in the previous month; c sets the managed sd equal to buy-and-hold's; rebalance monthly.
  - Harvey: weight = 10% ÷ σ̂, σ̂ = EWMA sd of daily returns (half-life 20 days; 10 and 90 also shown) using data to t−2; rebalance daily; leverage cap not specified.
  - Applied to an existing return stream (market, factors, futures, 60/40, risk parity). No entry or exit: the rule is pure sizing.
- **Primitive vs wrapper.** Primary P2 (vol is forecastable; expected return does not rise in proportion); secondary P1 (Harvey: scaling down after losses adds time-series momentum, explaining 45-60% of the cross-asset Sharpe gain).
- **Claimed mechanism.** High vol is not paid by proportionally higher expected return (Moreira-Muir); in equities and credit the leverage effect ties falling prices to rising vol (Harvey). Other side: holders who keep constant exposure through vol spikes or de-lever late.
- **Published claim.** Moreira-Muir, US market 1926-2015: alpha 4.86%/yr, Sharpe 0.42 → 0.52, breakeven ~56 bp a trade; alpha 2.12% with no leverage. Harvey, US equities 1926-2017: Sharpe 0.40 → ~0.48-0.51, vol of vol 4.6% → 1.8%; negligible Sharpe change for bonds, FX and commodities; thinner left tail in almost all. Barroso-Santa-Clara: risk-managed momentum "nearly doubles" the Sharpe ratio.
- **Decay and crowding.** Cederburg et al. (103 equity strategies): real-time versions generally earn lower Sharpe and certainty-equivalent returns than the unmanaged ones, from unstable spanning regressions.
- **Cost-floor note.** Monthly or daily exposure changes, not a round trip per signal; the Moreira-Muir breakeven (~56 bp a trade) is above 13 bp.
- **Event rate (estimate).** 12-250 sizing decisions a year; 2-5 independent vol regimes a year.
- **Applies to / testable here.** Equities, factors, futures. Y (daily perp returns; BTC or an equal-weight coin index as the stream).
- **Regime hypothesis.** Works where vol spikes come with falling prices (leverage effect); should fail where vol rises during rallies, as in crypto upside episodes.
- **Overlaps.** The sizing step in S-BRK-05, S-BRK-09 and S-BRK-11.

### S-BRK-15 Short volatility (variance risk premium): put-write and buy-write
- **Fidelity.** B. Index rules from an exchange-funded report and an encyclopaedia page; Whaley (2002) not read.
- **Sources.**
  - Callan Associates, "An Historical Evaluation of the CBOE S&P 500 BuyWrite Index Strategy", 2006, CBOE-funded, https://cdn.cboe.com/resources/education/research_publications/Callan_CBOE.pdf (read: full).
  - "CBOE S&P 500 PutWrite Index", Wikipedia, https://en.wikipedia.org/wiki/CBOE_S%26P_500_PutWrite_Index (read: full; cites Ennis Knupp 2009). P. Carr and L. Wu, "Variance Risk Premiums", *RFS* 22(3), 2009, https://ideas.repec.org/a/oup/rfinst/v22y2009i3p1311-1341..html (read: abstract).
  - C. Alexander and A. Imeraj, "The Bitcoin VIX and its variance risk premium", *J. of Alternative Investments*, 2020, https://sro.sussex.ac.uk/id/eprint/91094/ (read: abstract). C. Almeida, M. Grith, R. Miftachov and Z. Wang, "Risk Premia in the Bitcoin Market", arXiv:2410.15195, 2024, https://arxiv.org/abs/2410.15195 (read: abstract).
- **Rule.**
  - BXM: hold the S&P 500; write a one-month at-the-money call at each monthly expiry (third Friday); hold to expiry, cash-settled; repeat.
  - PUT: sell one-month at-the-money S&P 500 puts monthly, collateralized in 1- and 3-month T-bills (put count capped so the T-bills cover the maximum loss).
  - Data: index option prices. A crypto version needs Deribit options.
- **Primitive vs wrapper.** Primary P4 (paid a premium for bearing variance and crash risk); secondary P2. Wrapper: moneyness, tenor, collateral.
- **Claimed mechanism.** Implied volatility usually exceeds realized: option buyers pay for insurance and sellers bear negative skew. Limits to arbitrage: capital and crash risk.
- **Published claim.** BXM 1988-06 to 2006-08: 11.77%/yr vs 11.67% S&P, sd 9.29% vs 13.89%, Sharpe 0.77 vs 0.51, max DD −32.5% vs −47.4%. PUT 1986-07 to 2008-10: 10.32%/yr vs 8.77%, sd 9.91% vs 15.39%. Almeida et al.: the Bitcoin VRP exceeds the S&P 500's and is higher in low-vol regimes.
- **Decay and crowding.** BXM premium income had fallen back to early-1990s levels by 2006; lags in strong bull markets (1995-1998); negative skew and excess kurtosis.
- **Cost-floor note.** Option spreads apply, not the 13 bp perp model; not comparable.
- **Event rate (estimate).** 12 rolls a year; loss events are vol spikes, 1-2 a year.
- **Applies to / testable here.** Index and Bitcoin options. N (needs option prices or implied vol; perp funding is a different premium).
- **Regime hypothesis.** Earns in calm or falling vol; loses in vol spikes and crashes. Per Almeida et al., the Bitcoin premium is larger in low-vol regimes.
- **Overlaps.** The carry family (P4); S-BRK-16 (same option-implied data).

### S-BRK-16 Vol-of-vol cross-section (uncertainty about risk)
- **Fidelity.** A.
- **Sources.** G. Baltussen, S. van Bekkum and B. van der Grient, "Unknown Unknowns: Uncertainty About Risk and Stock Returns", *JFQA* 53(4), 2018, https://personal.eur.nl/vanbekkum/2018JFQA_unknown_unknowns.pdf (read: full).
- **Rule.**
  - VoV = sd of daily at-the-money implied vol (mean of the nearest-ATM call and put, maturity closest to 30 days) over the past 20 trading days ÷ the mean IV over that window; at least 12 observations.
  - Monthly quintile sort with a 1-day lag; long low VoV, short high VoV; value-weighted; hold one month.
  - Universe: US optionable common stocks 1996-2014; Europe 2002-2012.
- **Primitive vs wrapper.** Primary P3; secondary P2. Wrapper: quintiles, value weights.
- **Claimed mechanism.** Ambiguity-averse investors avoid high-VoV stocks, which are left to optimists who accept lower returns (limited participation). Higher VoV predicts falling turnover.
- **Published claim.** Source, US value-weighted: high minus low −0.69%/month (t −2.96), 4-factor alpha −0.60% (t −2.62); equal-weighted −0.50% (t −3.97). Europe ≈ −0.34%/month.
- **Decay and crowding.** Value-weighted excess return shrank across three subperiods (about −1.6%, −0.4%, −0.2% a month). Insignificant when VoV uses 3-12 months of IV.
- **Cost-floor note.** Monthly rebalance; a 50-70 bp monthly spread against two legs of turnover. 13 bp a round trip is small if turnover is moderate.
- **Event rate (estimate).** 12 cross-sectional rebalances a year.
- **Applies to / testable here.** US and European optionable stocks. N as published (needs per-coin implied vol; Deribit lists only a few coins). A realized vol-of-vol proxy on klines is a different variable.
- **Regime hypothesis.** Should be strongest when dispersion in uncertainty is high and participation limited; the source finds it in > 60% of months, not confined to recessions.
- **Overlaps.** S-BRK-15 (option-implied vol); the cross-sectional family (P3).

---

## Family notes

The 16 cards hold about four primitives. (1) P1 continuation after a move beyond a reference:
open-anchored (01, 03, 04, 05, 06, 07, 13-continuation) or N-day-high anchored (09, 10, 11, 12);
the reference, threshold and exit are wrapper. (2) P2 compression-to-expansion as a state (01, 02,
08), which predicts size, not sign; each card bolts a P1 direction rule onto it. (3) P2 as sizing
(14, and inside 05, 09, 11), not an entry. (4) Option-implied premia: P4 short vol (15) and P3
vol-of-vol (16), untestable here without options. The FX gap fade (13) is a lone P1 reversal.
Not mechanizable: Darvas (12). No primary found: London breakout (07). Exits unspecified: 02, 08, 11.
