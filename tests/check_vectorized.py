"""Check NumPy results against the sequential baseline."""

import argparse
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from model import generate_portfolio, simulate_range
from vectorized import run


def check_vectorized():
    portfolio = generate_portfolio(500, 2026)
    expected = simulate_range(portfolio, 0, 200, 2026)
    previous = None

    for batch_size in (1, 7, 64):
        args = argparse.Namespace(
            scenarios=200,
            seed=2026,
            batch_size=batch_size,
        )
        got, _ = run(portfolio, args)

        assert len(got) == len(expected), "Scenario count differs"

        # NumPy sums can introduce small floating-point differences.
        np.testing.assert_allclose(
            [r[0] for r in got],
            [r[0] for r in expected],
            rtol=0,
            atol=1e-10,
        )
        assert [r[1] for r in got] == [r[1] for r in expected], (
            "Breach flags differ"
        )

        if previous is not None:
            assert got == previous, "Results change with batch size"
        previous = got

        print(f"PASS: batch_size={batch_size}")

    print("ALL NUMPY CHECKS PASSED")


if __name__ == "__main__":
    check_vectorized()
