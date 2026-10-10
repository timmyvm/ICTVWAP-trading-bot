"""P2 power table. Inputs are the unconditional explore-quadrant statistics (explore_stats.py)
and counts from split_assignment.csv. Uses backtest.edge_lab.power and ledger only."""
import math
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[3]))
from backtest.edge_lab import power, ledger  # noqa: E402

T_EXP = 2.0
T_SEAL = ledger.bonferroni_t(5)
print(f"t bars: explore {T_EXP}, sealed bonferroni_t(5) = {T_SEAL:.3f}")
for m in (1, 2, 3, 4, 5, 6, 8, 10, 15, 20):
    print(f"  bonferroni_t({m}) = {ledger.bonferroni_t(m):.3f}")

# --- unconditional explore stats, top-50 half-A universe (bp) ---
SD = {1: 659.3, 7: 1812.0, 30: 4760.7}          # single-coin h-day open-to-open return sd
ICC = {1: 0.483, 7: 0.442, 30: 0.386}           # same-date intra-class correlation
SDW = {1: 592.3, 7: 1622.6, 30: 4031.6}         # 0.5/99.5% winsorised sd (sensitivity)
SPR = {1: 241.3, 7: 727.1, 30: 1904.9}          # random-sort quintile spread sd (10 names a leg)
IDX = {1: 452.5, 7: 1190.3, 30: 3235.8}         # EW top-10 half-A index sd
ABS = {1: 500.5, 7: 1390.9, 30: 3966.2}         # sd of |r_h|

# --- windows (non-overlapping h-day date windows) ---
G_EXP = {1: 1698, 7: 244, 30: 56}               # explore from 2020-05-09 (>= 10 top-50 names)
G_EB = dict(G_EXP)                              # early_B: same calendar (assumption: same listing pace)
G_LATE = {1: 638, 7: 91, 30: 21}                # 2025-01-01 .. 2026-09-30
N_EXP, N_LATE = 44, 100                         # names per date: explore top-50 A; late = top-50 A + top-50 B
SORT_MULT = 1.5                                 # assumption: a real sort's spread sd vs a random sort's
C_AB = 0.5                                      # assumption: corr of half-A and half-B spreads on the same date
RHO_IDIO = 0.05                                 # assumption: residual ICC after a market hedge

def mde(n, sd, t):
    return power.min_detectable_edge_bps(max(int(round(n)), 1), sd, t_bar=t)

def pooled(parts, t):
    """parts: list of (n_windows, window_sd). Returns MDE of the pooled mean."""
    n = sum(p[0] for p in parts)
    sd = math.sqrt(sum(p[0] * p[1] ** 2 for p in parts) / n)
    return mde(n, sd, t)

def win_sd(h, m, rho=None, sd=None):
    rho = ICC[h] if rho is None else rho
    sd = SD[h] if sd is None else sd
    return sd * math.sqrt(rho + (1 - rho) / m)

rows = []
def row(arch, case, h, exp, seal_pool, seal_late, cost_viable, note=""):
    rows.append((arch, case, h, exp, seal_pool, seal_late, cost_viable, note))

# TS_STATE raw (market-exposed): sign states (every coin-day has a sign) and extreme states (5 % of coin-days)
for h in (1, 7, 30):
    e = mde(G_EXP[h], win_sd(h, N_EXP), T_EXP)
    pool = pooled([(G_EB[h], win_sd(h, N_EXP)), (G_LATE[h], win_sd(h, N_LATE))], T_SEAL)
    late = mde(G_LATE[h], win_sd(h, N_LATE), T_SEAL)
    row("TS_STATE raw", "sign state, f=100%", h, e, pool, late, 39)
    f = 0.05
    m_e = N_EXP * (1 - (1 - f) ** h); m_l = N_LATE * (1 - (1 - f) ** h)
    act_e = 1 - (1 - f) ** (N_EXP * h); act_l = 1 - (1 - f) ** (N_LATE * h)
    e = mde(G_EXP[h] * act_e, win_sd(h, m_e), T_EXP)
    pool = pooled([(G_EB[h] * act_e, win_sd(h, m_e)), (G_LATE[h] * act_l, win_sd(h, m_l))], T_SEAL)
    late = mde(G_LATE[h] * act_l, win_sd(h, m_l), T_SEAL)
    row("TS_STATE raw", "extreme state, f=5%", h, e, pool, late, 39)

# TS_STATE hedged (alpha vs MKT_A10): residual sd from the random spread, residual ICC assumed 0.05
for h in (1, 7, 30):
    s_i = SPR[h] / math.sqrt(2 / 10)
    for case, f in (("sign state, f=100%", 1.0), ("extreme state, f=5%", 0.05)):
        m_e = N_EXP * (1 - (1 - f) ** h) if f < 1 else N_EXP
        m_l = N_LATE * (1 - (1 - f) ** h) if f < 1 else N_LATE
        we = win_sd(h, m_e, RHO_IDIO, s_i); wl = win_sd(h, m_l, RHO_IDIO, s_i)
        e = mde(G_EXP[h], we, T_EXP)
        pool = pooled([(G_EB[h], we), (G_LATE[h], wl)], T_SEAL)
        late = mde(G_LATE[h], wl, T_SEAL)
        row("TS_STATE hedged", case, h, e, pool, late, 78, "two legs (coin + hedge)")

# XS_RANK: quintile spread (10 a leg) and decile spread (5 a leg), real sort = 1.5 x random
for h in (1, 7, 30):
    for case, k in (("quintile, 10/leg", 1.0), ("decile, 5/leg", math.sqrt(2))):
        se = SPR[h] * SORT_MULT * k
        sl = se * math.sqrt((1 + C_AB) / 2)
        e = mde(G_EXP[h], se, T_EXP)
        pool = pooled([(G_EB[h], se), (G_LATE[h], sl)], T_SEAL)
        late = mde(G_LATE[h], sl, T_SEAL)
        row("XS_RANK", case, h, e, pool, late, 78, "full turnover, 26 bp/rebalance")
    # CARRY XS: ~35 names with funding -> 7 a leg
    se = SPR[h] * SORT_MULT * math.sqrt(10 / 7); sl = se * math.sqrt((1 + C_AB) / 2)
    row("CARRY (XS funding)", "quintile, 7/leg", h, mde(G_EXP[h], se, T_EXP),
        pooled([(G_EB[h], se), (G_LATE[h], sl)], T_SEAL), mde(G_LATE[h], sl, T_SEAL), 78, "price leg dominates noise")

# VOL_STATE: forward |r| difference, state on 15 % of coin-days, ICC of |r| assumed 0.5
for h in (1, 7, 30):
    f = 0.15
    m_e = N_EXP * (1 - (1 - f) ** h); m_l = N_LATE * (1 - (1 - f) ** h)
    we = win_sd(h, m_e, 0.5, ABS[h]); wl = win_sd(h, m_l, 0.5, ABS[h])
    row("VOL_STATE", "|r| after state, f=15%", h, mde(G_EXP[h], we, T_EXP),
        pooled([(G_EB[h], we), (G_LATE[h], wl)], T_SEAL), mde(G_LATE[h], wl, T_SEAL), float("nan"), "size, not sign; no cost ratio")

# CLOCK on MKT_A10 (market-wide): contrasts of bucket means, n_eff = 1/(1/n1 + 1/n2)
def neff(n1, n2):
    return 1.0 / (1.0 / n1 + 1.0 / n2)
G_EXP_D, G_LATE_D = 1698, 638
for case, share, sd in (("weekend vs weekday, per day", 2 / 7, IDX[1]),
                        ("turn of month (4 d) vs rest, per day", 4 / 30.4, IDX[1]),
                        ("one pre-stated hour vs rest (T2), per hour", 1 / 24, IDX[1] / math.sqrt(24))):
    ne = neff(G_EXP_D * share, G_EXP_D * (1 - share)) if "hour" not in case else neff(G_EXP_D, 23 * G_EXP_D)
    nl = neff(G_LATE_D * share, G_LATE_D * (1 - share)) if "hour" not in case else neff(G_LATE_D, 23 * G_LATE_D)
    nb = ne  # early_B duplicates the explore market path for market-wide buckets
    row("CLOCK", case, 1, mde(ne, sd, T_EXP), mde(ne + nl, sd, T_SEAL), mde(nl, sd, T_SEAL), 39,
        "market-wide: only late dates are new")

# EVENT (T2 calendars): 1-day market return on event days vs other days
for case, per_year in (("FOMC days (8/yr)", 8), ("CPI+NFP+FOMC days (~32/yr)", 32)):
    ne = neff(per_year * 1698 / 365, 1698); nl = neff(per_year * 638 / 365, 638)
    row("EVENT", case, 1, mde(ne, IDX[1], T_EXP), mde(ne + nl, IDX[1], T_SEAL), mde(nl, IDX[1], T_SEAL), 39,
        "market-wide: only late dates are new")

# FLOW_STATE OI flush (T2): distinct dates, scaled from H010 (8 coins: 25 explore / 9 late dates)
for case, de, dl in (("OI-tail flush, 50-100 coins (assumed 50/20 dates)", 50, 20),
                     ("OI-tail flush, 8 coins (H010 counts 25/9 dates)", 25, 9)):
    w = win_sd(1, 2)
    row("FLOW_STATE", case, 1, mde(de, w, T_EXP), mde(de + dl, w, T_SEAL), mde(dl, w, T_SEAL), 39)

print(f"\n{'archetype':<20}{'case':<46}{'h':>3}{'explore t2':>11}{'seal pool':>11}{'seal late':>11}{'cost-viable':>12}")
for r in rows:
    print(f"{r[0]:<20}{r[1]:<46}{r[2]:>3}{r[3]:>11.0f}{r[4]:>11.0f}{r[5]:>11.0f}{r[6]:>12.0f}  {r[7]}")

# Sharpe needed: market-timing over the late era alone
for yrs, lab in ((1.75, "late era"), (4.65 + 1.75, "early_B + late")):
    print(f"annual Sharpe a t={T_SEAL:.2f}/80% test can resolve over {lab} ({yrs} yr): "
          f"{(T_SEAL + 0.8416) / math.sqrt(yrs):.2f};  at t=2: {(2 + 0.8416) / math.sqrt(yrs):.2f}")
print("years needed for annual Sharpe 1.0 at t 2.58/80%:", round(power.years_for_sharpe(1.0, T_SEAL), 1),
      "; Sharpe 0.5:", round(power.years_for_sharpe(0.5, T_SEAL), 1))

# Deflated Sharpe equivalence: the t (= SR*sqrt(T)) at which DSR = 0.95 with var_sr = 1/T
def t_for_dsr(N, T=638):
    lo, hi = 0.0, 10.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if ledger.deflated_sharpe(mid / math.sqrt(T), T, N) < 0.95:
            lo = mid
        else:
            hi = mid
    return hi
print("\nDSR >= 0.95 needs an unclustered t (SR*sqrt(T)) of about:")
for N in (1, 3, 5, 10, 71, 200, 300, 375, 400, 450):
    print(f"  N = {N:>4}: t >= {t_for_dsr(N):.2f}   (bonferroni_t(N) = {ledger.bonferroni_t(N):.2f})")
print("ledger.total_trials() now:", ledger.total_trials())
