"""python3 -m backtest.edge_lab.selftest

Planted-edge recovery, null calibration, a lookahead guard that must catch a planted
lookahead, the cost constant, the statistics, and the ledger's refusals. If any of this
fails, no result from the harness may be read.
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

from backtest.edge_lab import ledger as L
from backtest.edge_lab import measure as M
from backtest.edge_lab import power as P


def _prices(n: int = 26_000, sd: float = 0.004, seed: int = 1, plant: np.ndarray | None = None,
            plant_bp: float = 0.0) -> pd.DataFrame:
    """Hourly random-walk OHLC. open[k+1] = open[k] * exp(r[k]); a decision at the close of t
    that is followed by +plant_bp on bar t+1's return is a planted edge of exactly that size."""
    rng = np.random.default_rng(seed)
    r = rng.normal(0, sd, n)
    if plant is not None:
        r[1:] += plant[:-1] * plant_bp / M.BPS
    idx = pd.date_range("2021-01-01", periods=n, freq="1h", tz="UTC")
    op = 100 * np.exp(np.concatenate([[0], np.cumsum(r)[:-1]]))
    return pd.DataFrame({"open": op, "close": np.append(op[1:], op[-1] * np.exp(r[-1]))}, index=idx)


def _rand_signal(n: int, p: float, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return np.where(rng.random(n) < p, rng.choice([-1.0, 1.0], n), 0.0)


def t_cost_constant() -> None:
    assert abs(M.ROUND_TRIP_BPS - 13.0) < 1e-9, M.ROUND_TRIP_BPS


def t_planted_edge_recovered() -> None:
    n, h = 26_000, 4
    sig = _rand_signal(n, 0.02, 7)
    px = _prices(n, plant=sig, plant_bp=30.0)
    s = pd.Series(sig, index=px.index)
    r = M.trade_return(px["open"], h)
    res = M.information_test(s, r, h=h)
    assert abs(res["gross_excess_bps"] - 30.0) < 15.0, res
    assert res["t_excess"] > 3.0, res
    assert 1.0 < res["cost_ratio"] < 4.0, res
    nul = M.null_shift_p(s, r, h=h, n_shifts=120)
    assert nul["p_value"] < 0.05, nul


def t_null_is_calibrated() -> None:
    n, h = 26_000, 4
    px = _prices(n, seed=3)
    r = M.trade_return(px["open"], h)
    hits = 0
    runs = 150
    for k in range(runs):
        s = pd.Series(_rand_signal(n, 0.02, 100 + k), index=px.index)
        t = M.information_test(s, r, h=h)["t_excess"]
        hits += abs(t) > 2.0
    rate = hits / runs
    assert rate < 0.13, f"false-positive rate {rate:.2%} at |t|>2 (expect ~5%)"


def t_null_shift_not_fooled() -> None:
    n, h = 26_000, 4
    px = _prices(n, seed=5)
    r = M.trade_return(px["open"], h)
    s = pd.Series(_rand_signal(n, 0.02, 11), index=px.index)
    assert M.null_shift_p(s, r, h=h, n_shifts=120)["p_value"] > 0.01


def t_truncation_guard() -> None:
    px = _prices(6_000, seed=9)
    causal = lambda d: (d["close"].pct_change(24) > 0).astype(float)          # noqa: E731
    future = lambda d: (d["close"].shift(-1) > d["close"]).astype(float)       # noqa: E731
    global_z = lambda d: ((d["close"] - d["close"].mean()) / d["close"].std() > 0).astype(float)  # noqa: E731
    assert M.truncation_guard(causal, px) == []
    assert M.truncation_guard(future, px) != [], "guard missed shift(-1) lookahead"
    assert M.truncation_guard(global_z, px) != [], "guard missed full-sample normalisation"


def t_hedge_removes_beta() -> None:
    n, h = 26_000, 4
    px = _prices(n, seed=21)
    r = M.trade_return(px["open"], h)
    s = pd.Series(1.0, index=px.index)             # always long: all drift, no timing
    res = M.information_test(s, r, h=h, mkt_ret=r)
    assert abs(res["beta_to_market"] - 1.0) < 1e-6, res
    assert abs(res["hedged_alpha_bps"] + M.ROUND_TRIP_BPS) < 1.0, res  # only the cost is left


def t_power_and_stats() -> None:
    assert abs(P.years_for_sharpe(1.0) - 8.1) < 0.1                   # (2 + 0.84)^2
    assert P.n_required(13, 100) > P.n_required(26, 100)
    assert L.deflated_sharpe(0.1, 1000, 1000) < L.deflated_sharpe(0.1, 1000, 10)
    assert L.deflated_sharpe(0.0, 1000, 1000) < 0.5
    assert abs(L.bonferroni_t(1) - 1.96) < 0.01 and L.bonferroni_t(10) > L.bonferroni_t(1)
    assert M.plateau_score(pd.DataFrame([[1, 9, 1], [1, 1, 1]]))["share_similar"] < 0.5
    assert M.plateau_score(pd.DataFrame([[8, 9, 8], [8, 8, 8]]))["share_similar"] == 1.0


def t_ledger_refusals() -> None:
    with tempfile.TemporaryDirectory() as td:
        repo, led = Path(td), Path(td) / "ledger.jsonl"
        g = lambda *a: subprocess.run(["git", "-C", td, "-c", "user.name=t", "-c", "user.email=t@t", *a],  # noqa: E731
                                      capture_output=True, text=True, check=True)
        g("init", "-q")
        pre = repo / "prereg_demo.md"
        pre.write_text("primary: X; bar: t>=3\n")
        try:
            L.register(pre, family="demo", n_cells=3, primaries=1, repo=repo, ledger=led)
            raise AssertionError("registered an untracked pre-registration")
        except RuntimeError:
            pass
        g("add", "."); g("commit", "-qm", "prereg")
        L.register(pre, family="demo", n_cells=3, primaries=1, repo=repo, ledger=led)
        for bad in (lambda: L.register(pre, family="demo", n_cells=3, primaries=1, repo=repo, ledger=led),
                    lambda: L.open_holdout("prereg_demo", repo=repo, ledger=led)):
            try:
                bad()
                raise AssertionError("ledger allowed a forbidden step")
            except RuntimeError:
                pass
        L.mark_audited("prereg_demo", "ok", led)
        assert L.open_holdout("prereg_demo", repo=repo, ledger=led) is True
        try:
            L.open_holdout("prereg_demo", repo=repo, ledger=led)
            raise AssertionError("holdout opened twice")
        except RuntimeError:
            pass
        assert L.total_trials(led) == L.LEGACY_TRIALS + 3
        # editing the bar after registering must block the holdout of a second prereg
        pre2 = repo / "prereg_two.md"
        pre2.write_text("bar: t>=3\n"); g("add", "."); g("commit", "-qm", "p2")
        L.register(pre2, family="demo", n_cells=1, primaries=1, repo=repo, ledger=led)
        L.mark_audited("prereg_two", "ok", led)
        pre2.write_text("bar: t>=1\n")
        try:
            L.open_holdout("prereg_two", repo=repo, ledger=led)
            raise AssertionError("holdout opened after the bar was edited")
        except RuntimeError:
            pass


TESTS = [t_cost_constant, t_planted_edge_recovered, t_null_is_calibrated, t_null_shift_not_fooled,
         t_truncation_guard, t_hedge_removes_beta, t_power_and_stats, t_ledger_refusals]


def main() -> int:
    failed = 0
    for t in TESTS:
        try:
            t()
            print(f"PASS  {t.__name__}")
        except Exception as e:  # noqa: BLE001 - a selftest reports every failure kind
            failed += 1
            print(f"FAIL  {t.__name__}: {type(e).__name__}: {e}")
    print("ALL PASS" if not failed else f"{failed} FAILED")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
