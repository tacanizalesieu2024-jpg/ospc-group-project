"""Automated check: every parallel version must give the sequential results.

Run from the repository root:  python tests/check_equivalence.py

Why we can compare EXACTLY (no tolerance) for the pool version: each scenario
draws from its own random stream (seed, scenario index) and runs the same
arithmetic in the same order, whichever process executes it. Versions that
change the order of additions (e.g. NumPy sums) will need a small tolerance.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pool  # noqa: E402
import sequential  # noqa: E402
from model import annual_irr, generate_portfolio, summarize  # noqa: E402


def check_irr():
    # Known answer: invest 100, receive 1 a month for 12 months plus 100 back.
    # Monthly rate is exactly 1%, so the annual IRR is 1.01**12 - 1.
    flows = [-100.0] + [1.0] * 11 + [101.0]
    expected = 1.01 ** 12 - 1
    assert abs(annual_irr(flows) - expected) < 1e-9, "annual_irr is wrong"
    print("OK  annual_irr matches a case with a known answer")


    lower_bound = 0.95 ** 12 - 1.0
    upper_bound = 1.05 ** 12 - 1.0

    assert abs(annual_irr([-100.0, 90.0]) - lower_bound) < 1e-9, (
        "annual_irr should return the lower bound for a monthly IRR below -5%"
    )
    assert abs(annual_irr([-100.0, 110.0]) - upper_bound) < 1e-9, (
        "annual_irr should return the upper bound for a monthly IRR above 5%"
    )
    print("OK  annual_irr returns the expected bounds for out-of-range returns")


def check_pool(scenarios, properties, seed):
    portfolio = generate_portfolio(properties, seed)
    base_args = argparse.Namespace(scenarios=scenarios, seed=seed)
    expected, _ = sequential.run(portfolio, base_args)
    for workers, chunksize in [(1, 0), (2, 0), (3, 7), (4, 1)]:
        args = argparse.Namespace(scenarios=scenarios, seed=seed,
                                  workers=workers, chunksize=chunksize)
        got, _ = pool.run(portfolio, args)
        assert len(got) == len(expected), "different number of scenarios"
        assert [r[1] for r in got] == [r[1] for r in expected], "breach flags differ"
        assert [r[0] for r in got] == [r[0] for r in expected], "IRRs differ"
        assert summarize(got) == summarize(expected), "summaries differ"
        print(f"OK  pool workers={workers} chunksize={chunksize or 'auto'} "
              f"identical to sequential ({scenarios} scenarios)")


def check_threads(scenarios, properties, seed):
    import threads
    portfolio = generate_portfolio(properties, seed)
    expected, _ = sequential.run(portfolio, argparse.Namespace(scenarios=scenarios, seed=seed))
    for workers, chunksize in [(1, 0), (2, 0), (3, 7), (4, 1)]:
        args = argparse.Namespace(scenarios=scenarios, seed=seed,
                                  workers=workers, chunksize=chunksize)
        got, _ = threads.run(portfolio, args)
        assert got == expected, "threads results differ from sequential"
        print(f"OK  threads workers={workers} chunksize={chunksize or 'auto'} "
              f"identical to sequential ({scenarios} scenarios)")


if __name__ == "__main__":
    check_irr()
    check_pool(scenarios=40, properties=50, seed=2026)
    check_threads(scenarios=40, properties=50, seed=2026)
    print("ALL CHECKS PASSED")
