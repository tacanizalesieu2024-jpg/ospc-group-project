"""Simulate batches of scenarios using NumPy arrays."""

import numpy as np

from model import DT, MONTHS, PARAMS, SQRT_DT, annual_irr, scenario_rng
def simulate_batch(portfolio, start, stop, seed):
    """Simulate scenarios from start up to, but excluding, stop."""
    p = PARAMS
    count = stop - start
    n = portfolio["n"]

    z_market = np.empty((count, MONTHS, 3))
    z_idio = np.empty((count, MONTHS, n))
    u_vacancy = np.empty((count, MONTHS, n))

    for row, scenario in enumerate(range(start, stop)):
        rng = scenario_rng(seed, scenario)
        z_market[row] = rng.standard_normal((MONTHS, 3))
        z_idio[row] = rng.standard_normal((MONTHS, n))
        u_vacancy[row] = rng.random((MONTHS, n))
    values = np.broadcast_to(portfolio["price"], (count, n)).copy()
    occupied = np.ones((count, n), dtype=bool)

    rent = np.asarray(portfolio["rent"])
    costs = np.asarray(portfolio["opex"]).sum()
    total_loan = portfolio["total_loan"]

    rate = np.full(count, p["rate0"])
    rent_index = np.ones(count)
    breached = np.zeros(count, dtype=bool)

    cash_flows = np.empty((count, MONTHS + 1))
    cash_flows[:, 0] = -(portfolio["total_price"] - total_loan)
    rate_step = p["rate_sigma"] * SQRT_DT
    rent_drift = p["rent_drift"] * DT
    rent_step = p["rent_sigma"] * SQRT_DT
    price_drift = p["price_drift"] * DT
    market_step = p["price_sigma_market"] * SQRT_DT
    idio_step = p["price_sigma_idio"] * SQRT_DT

    for month in range(MONTHS):
        rate += (
            p["rate_speed"] * (p["rate_mean"] - rate) * DT
            + rate_step * z_market[:, month, 0]
        )
        np.maximum(rate, p["rate_floor"], out=rate)

        rent_index *= (
            1.0 + rent_drift + rent_step * z_market[:, month, 2]
        )
        market_growth = (
            1.0 + price_drift + market_step * z_market[:, month, 1]
        )
        values *= (
            market_growth[:, None] + idio_step * z_idio[:, month, :]
        )
        total_value = values.sum(axis=1)

        draws = u_vacancy[:, month, :]
        occupied = np.where(
            occupied,
            draws >= p["p_vacate"],
            draws < p["p_fill"],
        )
        income = (occupied * rent).sum(axis=1)
        interest = total_loan * (rate + p["margin"]) / 12.0
        cash_flows[:, month + 1] = (
            (income - costs) * rent_index - interest
        )
        breached |= total_loan / total_value > p["covenant_ltv"]

    # Sell the properties and repay the loan in the final month.
    cash_flows[:, -1] += (
        total_value * (1.0 - p["sale_cost"]) - total_loan
    )

    return [
        (annual_irr(flows.tolist()), bool(flag))
        for flows, flag in zip(cash_flows, breached)
    ]


def run(portfolio, args):
    """Process all scenarios in batches, preserving their original order."""
    if args.batch_size < 1:
        raise ValueError("batch_size must be positive")
    if args.scenarios < 1 or portfolio["n"] < 1:
        raise ValueError("scenarios and properties must be positive")

    results = []
    for start in range(0, args.scenarios, args.batch_size):
        stop = min(start + args.batch_size, args.scenarios)
        results.extend(simulate_batch(portfolio, start, stop, args.seed))

    return results, 0.0


def parse_args():
    """Read simulation settings from the command line."""
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenarios", type=int, default=200)
    parser.add_argument("--properties", type=int, default=500)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--rep", type=int, default=1)
    parser.add_argument("--csv", default=None)

    args = parser.parse_args()
    if min(args.scenarios, args.properties, args.batch_size) < 1:
        parser.error("scenarios, properties and batch-size must be positive")

    return args


if __name__ == "__main__":
    from common import run_and_log

    args = parse_args()
    print(f"[numpy] batch_size={args.batch_size}")
    run_and_log(f"numpy_batch_{args.batch_size}", args, run)