"""Edge lab: the shared measurement harness for the chair + five-agent research team.

Nothing here generates ideas. It exists so that every agent measures an edge the same
way, with the repo's real cost model, and so that the number of things tried is counted
in one place. See docs/EDGE_LAB.md for the protocol.

    measure.py   the measurement battery (information test, nulls, hedged alpha, stability)
    power.py     how much data a claimed edge needs before a test can distinguish it from luck
    ledger.py    append-only trial ledger, pre-registration check, one-shot holdout, deflated Sharpe
    selftest.py  python3 -m backtest.edge_lab.selftest
"""
