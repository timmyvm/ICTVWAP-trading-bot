# The failure path — why every reel strategy died, and what the survivor does instead

Compiled 2026-09-12 from the DEVLOG after twelve mechanized reel/ICT strategies
across BTC, NAS100, gold and oil. Every one of them is built the same way:

    1. Draw a LEVEL (FVG, order block, session high/low, first-candle range,
       swing to be swept, volume-profile POC, fib zone).
    2. Wait for price to TOUCH or REACT to it (wick in, sweep, retest, close back).
    3. Enter AT the level.
    4. Put the stop just beyond the local wick / structure.
    5. Target a multiple (1:2, 1:3, 0.3:1, 10R) or the next level.

That construction produces two independent fatal properties, and usually both:

## Property A — location is not information

At the moment price touches a drawn level, its next direction is a coin flip.
Measured directly: for every bracket geometry the random-walk null win rate is
stop/(stop+target), and the strategies land ON it.

| strategy (DEVLOG) | market | win % observed | null for its bracket | information |
|---|---|---|---|---|
| v0.12 gold 5m FVG wick, 0.3:1 | XAU | 20.8 / 21.0 | 23.1 | none |
| v0.12c flipped, risk 1 : make 0.3 | XAU | 57.8 / 59.2 | 76.9 | none (below) |
| v0.14 session sweep + 1m FVG, 1:2 | NQ | 32.0 / 32.6 | 33.3 | none |
| v0.14b same, DOL targets | NQ | 28.8 / 27.1 | ~1/(1+RR) | none |
| v0.15 2C/3C liquidity grab, 1R half + 2R | BTC | TP1 49.6 (null 50), TP2\|TP1 68.0 (null 66.7) | — | none |
| v0.16 first-candle-range retest, 1:3 | NQ | 23.2 / 22.6 | 25.0 | none |
| v0.17 volume-profile POC pullback | BTC | PF 0.78 / 0.86 at low cost | — | NEGATIVE |
| v0.16b ORB (published), ATR stop | NQ | PF 1.10 / 1.44 at base cost | — | positive but small |

Changing the payoff map cannot fix this: under no information, E = 0 for every
target placement (v0.14b moved the win rate from 32 % to 28 % in exact
compensation for a 5R target). Confirmation candles do not fix it either
(v0.15: the "confirmation" left the hit rates on the null to a decimal).
Session filters do not fix it (v0.12d/e: the taught window was the worst one).

## Property B — the stop sits below the cost floor

"Stop just beyond the wick" is sold as small risk / big reward. It is the
mechanism by which fees + slippage become the largest term in the trade.

| strategy | stop size (% of price) | round-trip cost per R | outcome |
|---|---|---|---|
| VWAP 5m scalper (v0.3-v0.4) | ~0.1 | 0.6-1.0 R | fees = 85 % of the loss |
| v0.12 gold FVG, 0.3×ATR | ~0.02 | 0.3-0.5 R | −100 % in year one, 4 readings |
| v0.16 FCR retest | 0.05-0.07 | 0.35-0.72 R | −39 % / −33 % |
| v0.16b ORB ATR-stop | 0.06-0.09 | 0.20-0.27 R | real edge; dead at 1.5-2.6× cost |
| **v0.10c bracket (validated)** | **~1.0 (3×ATR)** | **~0.05 R** | +369 % unseen era |

The tight-stop law, confirmed seven times: a stop smaller than roughly ten
round-trip costs cannot be rescued by any entry, because the cost is charged on
every loser and recovered on none.

## The path, inverted — what the survivor does

v0.10c (1H |close − EMA200| ≥ 1 ATR → enter WITH the move, symmetric 3×ATR
bracket) is the negative image of the reel construction, step for step:

| reel step | v0.10c |
|---|---|
| draw a level | no level — a STATE (distance from the mean) |
| wait for a touch / reaction | enter immediately, with the move, no confirmation |
| enter at the level | enter at market on the closed signal candle |
| stop beyond the wick | stop at 3×ATR — costs ≈ 5 % of R |
| fixed R:R or next level | symmetric bracket — no payoff fantasy, the WIN RATE carries it |
| killzone / session gate | none (24/7); the edge is in the state, not the clock |

Its information is +8 points over the null (58 % vs 50 %) across ~22,500 trades
in five markets. That number, and the 0.05 R cost share, are the two things
none of the reels have.

## The screen (apply BEFORE mechanizing anything new)

1. Is the entry a state or a location? Location → expect ~0 information.
2. Stop ≥ 10 round-trip costs? At Bybit BTC (0.13 % RT) that means ≥ 1.3 % of
   price; at futures-CFD (0.014 %) ≥ 0.14 %. Smaller → expect the cost floor.
3. Does profitability depend on the R:R number? If yes, it depends on nothing.
4. Does it need a confirmation candle? Then the entry is late by construction.
5. Does it only work in a session? Then it needs to explain the mechanism.

Anything failing 1 or 2 can still be run for the record (it is cheap), but the
prior is the table above. Anything passing all five is worth a pre-registration.
