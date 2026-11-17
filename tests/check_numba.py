"""Check that Numba produces the same results as sequential Python."""

import numpy as np

from src.model import generate_portfolio, simulate_scenario
from src.numba_version import simulate_scenario_numba


def check_numba(scenarios=40, properties=500, seed=2026):
    """Compare IRR and LTV results for identical Monte Carlo scenarios."""

    # Generate one portfolio shared by both implementations.
    portfolio = generate_portfolio(properties, seed)

    max_irr_difference = 0.0

    # Test every scenario using the same seed and portfolio.
    for s in range(scenarios):

        # Original sequential implementation.
        original_irr, original_breach = simulate_scenario(
            portfolio, s, seed
        )

        # Numba-accelerated implementation.
        numba_irr, numba_breach = simulate_scenario_numba(
            portfolio, s, seed
        )

        # Check IRR within a small floating-point tolerance.
        difference = abs(original_irr - numba_irr)
        max_irr_difference = max(max_irr_difference, difference)

        assert np.isclose(
            original_irr, numba_irr, rtol=1e-10, atol=1e-12
        ), f"IRR mismatch in scenario {s}"

        # LTV breach flags must match exactly.
        assert original_breach == numba_breach, (
            f"LTV mismatch in scenario {s}"
        )

    print(f"OK: Numba matches sequential ({scenarios} scenarios)")
    print(f"Maximum IRR difference: {max_irr_difference:.3e}")
    print("ALL NUMBA CHECKS PASSED")


if __name__ == "__main__":
    check_numba()
