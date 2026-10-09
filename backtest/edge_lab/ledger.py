"""Append-only trial ledger, pre-registration check, one-shot holdout, deflated Sharpe.

Why this exists. A team of agents can test far more ideas per hour than one session can,
and the best of N zero-edge ideas looks like a real edge once N is large (the expected
maximum of N standard normals is ~sqrt(2 ln N)). So the one number nobody may lose track of
is N. Every pre-registered cell and every exploratory screen is appended here, and the
significance of any result is judged against the TOTAL, not against the cells of the
experiment that happened to win.

Rules the code enforces (an agent that bypasses them leaves the bypass in git history):
  * a pre-registration must be a committed, unmodified file before it can be registered;
  * holdout data is opened once per pre-registration, and only after the engine is audited;
  * the pre-registration file must be byte-identical to what was registered when the
    holdout is opened (no editing the bar after seeing the exploration era).
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from scipy.stats import norm

REPO = Path(__file__).resolve().parents[2]
LEDGER = Path(__file__).with_name("ledger.jsonl")

# DEVLOG v0.1 -> v0.34: the user counts 34 strategies, "about double" with variations.
# Refine from DEVLOG if you can; never lower it.
LEGACY_TRIALS = 68

EULER_GAMMA = 0.5772156649015329


# --------------------------------------------------------------------------- git helpers
def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=False)


def committed_hash(path: Path, repo: Path = REPO, require_pushed: bool = False) -> str:
    """Hash of the last commit that touched `path`; raises if the file is untracked or dirty."""
    rel = os.path.relpath(Path(path).resolve(), Path(repo).resolve())
    if _git(repo, "ls-files", "--error-unmatch", rel).returncode != 0:
        raise RuntimeError(f"{rel} is not tracked by git: commit the pre-registration first")
    if _git(repo, "status", "--porcelain", "--", rel).stdout.strip():
        raise RuntimeError(f"{rel} has uncommitted changes: commit the pre-registration first")
    h = _git(repo, "log", "-1", "--format=%H", "--", rel).stdout.strip()
    if not h:
        raise RuntimeError(f"no commit found for {rel}")
    if require_pushed and not _git(repo, "branch", "-r", "--contains", h).stdout.strip():
        raise RuntimeError(f"{rel} is committed but not pushed ({h[:8]}): push before computing any result")
    return h


def _sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# --------------------------------------------------------------------------- ledger io
def _read(ledger: Path = LEDGER) -> list[dict]:
    if not Path(ledger).exists():
        return []
    return [json.loads(line) for line in Path(ledger).read_text().splitlines() if line.strip()]


def _append(rec: dict, ledger: Path = LEDGER) -> dict:
    rec = {"t": datetime.now(timezone.utc).isoformat(timespec="seconds"), **rec}
    with open(ledger, "a") as f:
        f.write(json.dumps(rec, sort_keys=True) + "\n")
    return rec


def events(prereg_id: str, ledger: Path = LEDGER) -> list[str]:
    return [r["event"] for r in _read(ledger) if r.get("id") == prereg_id]


# --------------------------------------------------------------------------- lifecycle
def register(prereg_path: Path, *, family: str, n_cells: int, primaries: int,
             repo: Path = REPO, ledger: Path = LEDGER, require_pushed: bool = False) -> dict:
    """Step 2 of the protocol. n_cells = every variant this experiment will evaluate
    (primary + secondaries + diagnostics); primaries = the cells that can pass the verdict."""
    pid = Path(prereg_path).stem
    if "registered" in events(pid, ledger):
        raise RuntimeError(f"{pid} is already registered")
    if n_cells < primaries or primaries < 1:
        raise ValueError("need n_cells >= primaries >= 1")
    h = committed_hash(prereg_path, repo, require_pushed)
    return _append(dict(event="registered", id=pid, family=family, n_cells=int(n_cells),
                        primaries=int(primaries), prereg=os.path.relpath(Path(prereg_path).resolve(), Path(repo).resolve()),
                        prereg_commit=h, prereg_sha256=_sha256(prereg_path)), ledger)


def log_exploration(family: str, n_cells: int, note: str, ledger: Path = LEDGER) -> dict:
    """Every screen run outside a pre-registration still counts as trials. Log it."""
    return _append(dict(event="exploration", id=f"explore:{family}", family=family,
                        n_cells=int(n_cells), note=note), ledger)


def mark_audited(prereg_id: str, auditor_note: str, ledger: Path = LEDGER) -> dict:
    """Called by the chair after the auditor signs off on the ENGINE (not on any result)."""
    ev = events(prereg_id, ledger)
    if "registered" not in ev:
        raise RuntimeError(f"{prereg_id} is not registered")
    return _append(dict(event="engine_audited", id=prereg_id, note=auditor_note), ledger)


def open_holdout(prereg_id: str, *, repo: Path = REPO, ledger: Path = LEDGER) -> bool:
    """One-shot. Returns True exactly once per pre-registration."""
    ev = events(prereg_id, ledger)
    if "registered" not in ev:
        raise RuntimeError(f"{prereg_id} is not registered")
    if "engine_audited" not in ev:
        raise RuntimeError(f"{prereg_id}: the engine has not been audited, the holdout stays closed")
    if "holdout_opened" in ev:
        raise RuntimeError(f"{prereg_id}: the holdout was already opened; a second look is a new pre-registration")
    reg = next(r for r in _read(ledger) if r.get("id") == prereg_id and r["event"] == "registered")
    path = Path(repo) / reg["prereg"]
    if not path.exists() or _sha256(path) != reg["prereg_sha256"]:
        raise RuntimeError(f"{prereg_id}: the pre-registration file changed after it was registered")
    _append(dict(event="holdout_opened", id=prereg_id), ledger)
    return True


def record_verdict(prereg_id: str, verdict: str, summary: str, ledger: Path = LEDGER) -> dict:
    if "holdout_opened" not in events(prereg_id, ledger):
        raise RuntimeError(f"{prereg_id}: no holdout was opened, so there is nothing to give a verdict on")
    return _append(dict(event="verdict", id=prereg_id, verdict=verdict, summary=summary), ledger)


def total_trials(ledger: Path = LEDGER, legacy: int = LEGACY_TRIALS) -> int:
    return legacy + sum(r.get("n_cells", 0) for r in _read(ledger) if r["event"] in ("registered", "exploration"))


# --------------------------------------------------------------------------- statistics
def bonferroni_t(m_primaries: int, alpha: float = 0.05) -> float:
    """Two-sided normal-approximation t bar across the pre-registered primaries."""
    return float(norm.ppf(1 - alpha / (2 * max(m_primaries, 1))))


def expected_max_sharpe(n_trials: int, var_sr: float) -> float:
    """Bailey & Lopez de Prado (2014): the Sharpe the best of N zero-edge trials reaches by luck."""
    if n_trials <= 1:
        return 0.0
    return math.sqrt(var_sr) * ((1 - EULER_GAMMA) * norm.ppf(1 - 1.0 / n_trials)
                                + EULER_GAMMA * norm.ppf(1 - 1.0 / (n_trials * math.e)))


def deflated_sharpe(sr: float, T: int, n_trials: int, skew: float = 0.0, kurt: float = 3.0,
                    var_sr: Optional[float] = None) -> float:
    """Probability the true Sharpe is > 0 after accounting for N trials (Bailey & Lopez de Prado).

    sr      per-period (NOT annualised) Sharpe of the selected strategy
    T       number of periods behind it
    n_trials   use total_trials(), not this experiment's cell count
    var_sr  variance of Sharpe estimates across trials; default 1/T, the sampling variance of
            one estimate under no edge (a conservative stand-in when trial Sharpes weren't kept)
    """
    if T < 3:
        return float("nan")
    v = (1.0 / T) if var_sr is None else var_sr
    sr0 = expected_max_sharpe(n_trials, v)
    denom = math.sqrt(max(1e-12, 1 - skew * sr + (kurt - 1) / 4.0 * sr * sr))
    return float(norm.cdf((sr - sr0) * math.sqrt(T - 1) / denom))
