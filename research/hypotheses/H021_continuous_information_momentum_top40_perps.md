# H021: Continuity-filtered residual momentum ("frog in the pan"), top-40 USDT-M perps

**Family:** cross-sectional momentum and reversal (weekly-or-slower rebalance).

**Claim:** Continuation after a 14-day residual move is concentrated in coins whose move came as many
small same-signed days. Moves that came as one or two jump days (listing pops, pumps, liquidation
spikes) do not continue. A dollar-neutral book long continuous winners and short continuous losers earns
about +80 bp gross per 14-day rebalance, and the continuous half beats the jumpy half by about 50 bp.

## Scout's assessment (read this first)

- Predicted 80 bp gross per rebalance is at the chair's ~80 bp bar and gives a ratio of 3.1 against the
  harness's 26 bp, but the number rests on an analogy from equities. **No crypto study of this
  mechanism turned up in my searches** (query: "frog in the pan" / information discreteness with
  cryptocurrency; no hit). That is not my reason for proposing it; my reason is that it targets the
  failure mode the crypto momentum studies themselves report (see Mechanism, part 3).
- It is a refinement of H020, not an independent bet. If the base effect is absent, the filter can still
  show a sign difference between continuous and jumpy names, which is why it is worth its own card. The
  two should be pre-registered together as a family of two primaries.
- Power is poor (see Funnel and power). My subjective chance of a net-positive mean with t >= 2 on the
  continuous-only book is about 1 in 10.

## Mechanism

**1. Who is on the other side.** Inattentive investors. Da, Gurun and Warachka (2014, Review of Financial
Studies 27(7):2171-2218; abstract fetched) argue that investors pay less attention to information that
arrives gradually than to infrequent dramatic news. Stocks whose past return came from steady small
updates keep drifting; stocks with the same cumulative return from discrete news do not. Their
momentum profit falls from 5.94 % for continuous-information stocks to -2.07 % for discrete-information
stocks, and the continuous drift "does not reverse in the long run". Media coverage coincides with
discrete news and weakens the continuous drift. The payee is whoever holds the stock that has been
steadily mispriced; the payers are those who have not noticed a slow trend.

**2. Why it should persist, and the limit to arbitrage.** Attention is scarce and arbitrage in
steady-trend names is not riskless: shorting a steady loser still carries squeeze risk and funding.
Whether crypto attention behaves like equity attention is unsourced for crypto.

**3. Why crypto is a plausible place for it.** The crypto momentum papers describe exactly the jump
problem. Grobys et al. (2025, Financial Markets and Portfolio Management) find that a single coin's
jump can make momentum insignificant and that momentum is subject to severe crashes. Han, Kang and Ryu
(working paper, journal status not verified) find that losers rebound sharply and cause large short-leg
losses, and that outside a few large coins most coins reverse. If the reversal and the rebounds come
mostly from jump-driven moves (pumps and spikes), then screening those out should raise the spread and
cut the squeeze tail. That is a testable statement and it can fail.

**4. What I expect now.** The base momentum has decayed in tradable perps (see H020). I assume the
continuous-information half does better than the unconditional momentum by a factor of 1.5. That factor
is my assumption; I retrieved no unconditional momentum figure from Da et al., only the 5.94 % and
-2.07 % endpoints.

## Prediction

- Sign: positive for the continuous-only book; the continuous half exceeds the jumpy half.
- Formation 14 daily bars, `h` = 14 daily bars, same timing as H020 (decision at the close of day t,
  fill at the next open, exit 14 bars later).
- Numbers: **+80 bp gross per rebalance** for the continuous-only book (range -40 to +180 bp). Gradient:
  continuous-half spread about 80 bp, jumpy-half spread about 30 bp, difference **+50 bp**.
- Where it comes from: 1.5 x H020's 55 bp = 82 bp. The jumpy-half 30 bp makes the two halves average to
  H020's 55 bp. Soft, and I will not defend the second digit.
- Secondary prediction: the 1st-percentile 14-day return of the short leg is less severe than H020's,
  because steady decliners are less likely to spike than jump-prone coins.

## Variables (known at the close of day t, UTC)

Data: same fields as H020 (Binance USDT-M daily klines, funding history, symbol list). The daily panel
is not yet held.

1. `r`, `M[-i,s]`, `beta[i,t]`, `e[i,s]` and `S[i,t]` exactly as in H020 (leave-one-out universe index,
   90-day beta shrunk halfway to 1, 14-day sum of residual log returns).
2. `n_pos[i,t]` and `n_neg[i,t]` = counts of days in the 14-day window with `e` > 0 and `e` < 0.
3. Information discreteness `ID[i,t]` = sign(`S[i,t]`) x (`n_neg` - `n_pos`) / 14. Low (negative) ID is
   continuous in the direction of the move; high ID is jumpy. A winner with 11 up days and 3 down days has
   ID about -0.57; a loser with 11 down days and 3 up days also has ID about -0.57. It is a state of the
   path shape, not a level.
4. Book: Long set = top tercile on `S` AND `ID` at or below the median ID within that tercile. Short set
   = bottom tercile on `S` AND `ID` at or below the median ID within that tercile. Equal weight, equal
   dollar legs (about 6 to 7 names each).
5. Comparison book (the "jumpy half"): the same terciles with ID above the median. The hypothesis is the
   difference between the two books, not only the level of the first.

The median split is used because the claim is relative continuity and a finer cut would cut breadth in a
40-name universe. The statistician may add a Fama-MacBeth version with `S`, `ID` and `S x ID` as
regressors, which uses all 40 names and also controls the mechanical link between ID and the size of S
(a coin with more up days tends to have a larger S).

## Universe (point-in-time)

Identical to H020: symbol list from the archive's own directory listing; onboarded 90+ days; 28 of the
last 30 days with volume; top 40 by trailing 30-day median quote volume; index perps excluded; ticker
migrations mapped; delisted symbols kept while tradable, closed at the last close. The same survivorship
caveats apply, including that only one delisted symbol (LUNAUSDT) was spot-checked in the archive and
the BTCSTUSDT zombie-row question is open.

## What is neutralised, and how

Same as H020: market beta through residual returns against the leave-one-out universe index, with
realised beta to that index and to BTC reported by regression and hedged alpha as co-primary. The
liquidity tilt is reported, not removed. One new risk: choosing the smooth half can tilt toward lower
volatility coins, so report the volatility and liquidity tilt of each book. The H020 raw-return
comparator applies here too.

## Costs and funding

Harness convention (26 bp per rebalance at full turnover), plus measured turnover as a secondary line
and the 13/20/30 bp sweep. The continuity filter makes membership noisier than H020's, so turnover is
likely higher (I guess 0.75 or more per leg). With ~13 positions per rebalance, a given cost buys fewer
names. Funding is the real settled amount on each leg.

## Funnel and power

- Same calendar as H020: 26 rebalances per year per phase, about 160 observations over ~6.2 years, 14
  phase offsets reported together, never the best phase. About 13 positions per rebalance.
- Noise: with 6 to 7 names per leg the sd of the 14-day spread is larger, about 610 bp in my prior. The
  minimum detectable edge at 80 % power and t = 2 is about 2.84 x 610 / sqrt(160) = 137 bp, well above my
  predicted 80 bp and above the 50 bp gradient. Expected gross Sharpe is about 0.67.
- The gradient test is better run as the `S x ID` interaction in a cross-sectional regression than as a
  difference of two small portfolios. Two primaries (H020 and H021) need a family-wise correction.
- Trial accounting: this card, H020 and the rank-on-distance-from-high secondary are one signal family
  with ranks that overlap heavily. They should not be counted as independent evidence for each other.

## Falsifier

Drop the hypothesis if any of these holds:
1. The continuous half does not beat the jumpy half: the gradient is at or below zero over the full
   sample, or the interaction coefficient is not positive.
2. The continuous-only book fails any H020 falsifier (hedged gross at or below 26 bp, IC at or below 0.01
   on the continuous names, sign unstable across phases, one coin or one episode needed).
3. The gradient disappears once S is controlled (the Fama-MacBeth interaction is zero), meaning ID was
   only a proxy for the size of the move.
4. The short leg's worst-percentile loss is no better than H020's, which removes the squeeze-protection
   story.

## Not claimed

- No claim that base momentum exists; the gradient can be positive with a zero or negative average.
- No claim about long-run reversal. Da et al. find none after continuous news, but I make no prediction
  past 14 days.
- No claim about 1-day reversal or about the kline-level shape of intraday paths. ID uses daily residual
  signs only.
- No claim that attention in crypto works through media coverage; I have no social or news data.
- No claim that the filter's 80 bp is reliable. It is an analogy-based guess, flagged as such.
- Nothing about funding or open-interest crowding as a conditioner; that belongs in the carry and
  forced-flow families and would duplicate their trials.

## Citation status

Fetched this session: Da, Gurun and Warachka (abstract, RePEc); Daniel and Moskowitz (NBER w20439);
Liu, Tsyvinski and Wu (NBER w25882); Borri et al. (arXiv 2510.14435, preprint); Fieberg, Liedtke and
Zaremba 2024; Sila et al. 2025; Grobys et al. 2025 (abstract and Springer page); Han, Kang and Ryu
(working paper PDF). Recalled and not re-verified: Hong and Stein 1999, George and Hwang 2004, Barroso
and Santa-Clara 2015, Lou and Polk 2022.
