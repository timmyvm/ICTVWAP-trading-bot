# v0.29-live — live earnings reader: results

Scored 2026-11-26 17:55 New York time by `python backtest/live_earnings_reader.py --score`. Every call is scored from the first regular-session open after its decision date (adjusted open) to the adjusted close of the 20th session; costs 0.10 % per side plus 3 %/yr short financing on DOWN calls. Hit = the move went the called way, before costs; hit rates and means use closed calls only.

## Counts

| predictions | with a view (> 0.50) | trades | pending | open | closed |
|---:|---:|---:|---:|---:|---:|
| 390 | 355 | 0 | 0 | 0 | 0 |

## Calibration: every call with confidence > 0.50, traded or not

| confidence | closed | open | pending | hit rate | mean net |
|---|---:|---:|---:|---:|---:|
| [0.50-0.60) | 53 | 196 | 8 | 49 % (26/53) | -2.20 % |
| [0.60-0.70) | 16 | 82 | 0 | 50 % (8/16) | -3.88 % |
| [0.70-0.80) | 0 | 0 | 0 | n/a | n/a |
| [0.80-0.90) | 0 | 0 | 0 | n/a | n/a |
| [0.90-1.00] | 0 | 0 | 0 | n/a | n/a |
| all | 69 | 278 | 8 | 49 % (34/69) | -2.59 % |

## Paper trades (confidence >= 0.70: 1 % of the portfolio; >= 0.90: 2 %)

Total pnl_pct (size x net, share of the portfolio): closed +0.000 %; including open marks +0.000 %.


## Model (model.json) on the same events

Model calls on 388 recorded events (2 skipped: no s1 or reaction).

| model confidence | closed | open | pending | hit rate | mean net |
|---|---:|---:|---:|---:|---:|
| [0.50-0.60) | 87 | 292 | 9 | 54 % (47/87) | -1.17 % |
| [0.60-0.70) | 0 | 0 | 0 | n/a | n/a |
| [0.70-0.80) | 0 | 0 | 0 | n/a | n/a |
| [0.80-0.90) | 0 | 0 | 0 | n/a | n/a |
| [0.90-1.00] | 0 | 0 | 0 | n/a | n/a |
| all | 87 | 292 | 9 | 54 % (47/87) | -1.17 % |

Head to head on closed events where Claude had a view: Claude 34 of 69, model 38 of 69; same direction on 61 of 69.
