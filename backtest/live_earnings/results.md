# v0.29-live — live earnings reader: results

Scored 2026-10-29 18:00 New York time by `python backtest/live_earnings_reader.py --score`. Every call is scored from the first regular-session open after its decision date (adjusted open) to the adjusted close of the 20th session; costs 0.10 % per side plus 3 %/yr short financing on DOWN calls. Hit = the move went the called way, before costs; hit rates and means use closed calls only.

## Counts

| predictions | with a view (> 0.50) | trades | pending | open | closed |
|---:|---:|---:|---:|---:|---:|
| 136 | 117 | 0 | 0 | 0 | 0 |

## Calibration: every call with confidence > 0.50, traded or not

| confidence | closed | open | pending | hit rate | mean net |
|---|---:|---:|---:|---:|---:|
| [0.50-0.60) | 0 | 53 | 32 | n/a | n/a |
| [0.60-0.70) | 0 | 16 | 16 | n/a | n/a |
| [0.70-0.80) | 0 | 0 | 0 | n/a | n/a |
| [0.80-0.90) | 0 | 0 | 0 | n/a | n/a |
| [0.90-1.00] | 0 | 0 | 0 | n/a | n/a |
| all | 0 | 69 | 48 | n/a | n/a |

## Paper trades (confidence >= 0.70: 1 % of the portfolio; >= 0.90: 2 %)

Total pnl_pct (size x net, share of the portfolio): closed +0.000 %; including open marks +0.000 %.


## Model (model.json) on the same events

Model calls on 136 recorded events (0 skipped: no s1 or reaction).

| model confidence | closed | open | pending | hit rate | mean net |
|---|---:|---:|---:|---:|---:|
| [0.50-0.60) | 0 | 87 | 49 | n/a | n/a |
| [0.60-0.70) | 0 | 0 | 0 | n/a | n/a |
| [0.70-0.80) | 0 | 0 | 0 | n/a | n/a |
| [0.80-0.90) | 0 | 0 | 0 | n/a | n/a |
| [0.90-1.00] | 0 | 0 | 0 | n/a | n/a |
| all | 0 | 87 | 49 | n/a | n/a |

Head to head on closed events where Claude had a view: Claude 0 of 0, model 0 of 0; same direction on 0 of 0.
