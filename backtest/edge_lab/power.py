"""Power: how much data a claimed edge needs before a test can see it.

v0.31 lost two verdicts to trade count, not to edge (about 10 setups a year against a bar
of 60). Run these BEFORE pre-registering, so the bar is reachable. They use only counts and
the noise level, never a P&L.
"""

from __future__ import annotations

import math

from scipy.stats import norm


def n_required(edge_bps: float, sd_bps: float, t_bar: float = 2.0, power: float = 0.8) -> int:
    """Independent trades needed to detect a mean of `edge_bps` when each trade has sd `sd_bps`."""
    if edge_bps <= 0:
        raise ValueError("edge must be positive")
    return math.ceil(((t_bar + norm.ppf(power)) * sd_bps / edge_bps) ** 2)


def min_detectable_edge_bps(n: int, sd_bps: float, t_bar: float = 2.0, power: float = 0.8) -> float:
    """Smallest true mean per trade a test with n independent trades reaches `power` on."""
    return (t_bar + norm.ppf(power)) * sd_bps / math.sqrt(n)


def years_for_sharpe(sr_annual: float, t_bar: float = 2.0, power: float = 0.8) -> float:
    """Years of daily-ish data to detect a true annual Sharpe: the SE of an annual Sharpe is ~1/sqrt(years)."""
    return ((t_bar + norm.ppf(power)) / sr_annual) ** 2


def feasible(edge_bps: float, sd_bps: float, trades_per_year: float, years: float,
             t_bar: float = 2.0, power: float = 0.8) -> dict:
    """Can the planned sample size resolve the edge the hypothesis predicts?"""
    need = n_required(edge_bps, sd_bps, t_bar, power)
    have = trades_per_year * years
    return dict(n_needed=need, n_available=have, ok=have >= need,
                min_detectable_bps=min_detectable_edge_bps(max(int(have), 1), sd_bps, t_bar, power))
