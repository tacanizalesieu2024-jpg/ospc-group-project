"""Shared model code used by every version (sequential, pool, ...).

Workload: Monte Carlo risk of a portfolio of Madrid rental properties financed
with a floating-rate, interest-only loan.

One scenario = one possible 10-year future, simulated month by month.
For each scenario we return:
  * the annual IRR of the fund's equity cash flows, and
  * whether the loan-to-value (LTV) covenant was breached in any month.

The versions differ ONLY in how they distribute the scenarios over workers.
Everything a scenario computes lives here, so results are comparable.
"""

import math

import numpy as np

MONTHS = 120  # 10 years
DT = 1.0 / 12.0
SQRT_DT = math.sqrt(DT)

# Illustrative parameters. TODO (team): calibrate with INE, Madrid open data
# and ECB Euribor history, and document the sources in the report.
PARAMS = {
    # Portfolio
    "mean_price": 350_000.0,   # EUR, median purchase price
    "price_sigma": 0.35,       # dispersion of purchase prices (lognormal)
    "yield_low": 0.04,        # gross rental yield, lower bound
    "yield_high": 0.054,       # gross rental yield, upper bound
    "opex_ratio": 0.25,        # running costs as a share of initial rent
    "initial_ltv": 0.60,       # loan = 60% of purchase price
    # Loan
    "margin": 0.015,           # spread over Euribor
    "covenant_ltv": 0.70,      # breach if loan / value goes above this
    # Euribor (mean-reverting process)
    "rate0": 0.032386,
    "rate_mean": 0.009771,
    "rate_speed": 0.30,
    "rate_sigma": 0.004949,
    "rate_floor": -0.005,
    # Prices
    "price_drift": 0.0781,       # per year
    "price_sigma_market": 0.0326,  # market-wide shock, per year
    "price_sigma_idio": 0.08,    # property-specific shock, per year
    # Rents
    "rent_drift": 0.0229,
    "rent_sigma": 0.0127,
    # Vacancy (monthly probabilities)
    "p_vacate": 0.020833,          # occupied -> vacant
    "p_fill": 1.0,            # vacant -> occupied
    # Exit
    "sale_cost": 0.03,         # selling costs as a share of value
}


def portfolio_rng(seed):
    """Random stream used only to create the portfolio."""
    return np.random.default_rng(np.random.SeedSequence(entropy=seed, spawn_key=(0,)))


def scenario_rng(seed, scenario):
    """Independent, reproducible random stream for one scenario.

    Same stream that SeedSequence(seed).spawn(2)[1].spawn(N)[scenario] gives.
    Because the stream depends only on (seed, scenario), a scenario produces
    the same numbers whichever worker runs it and in whatever order.
    """
    return np.random.default_rng(
        np.random.SeedSequence(entropy=seed, spawn_key=(1, scenario))
    )


def generate_portfolio(n_properties, seed):
    """Create a synthetic portfolio. Returns plain Python lists and floats."""
    p = PARAMS
    rng = portfolio_rng(seed)
    price = p["mean_price"] * np.exp(p["price_sigma"] * rng.standard_normal(n_properties))
    gross_yield = rng.uniform(p["yield_low"], p["yield_high"], n_properties)
    rent = price * gross_yield / 12.0          # monthly rent
    opex = rent * p["opex_ratio"]              # monthly running costs
    total_price = float(price.sum())
    return {
        "n": n_properties,
        "price": price.tolist(),
        "rent": rent.tolist(),
        "opex": opex.tolist(),
        "total_price": total_price,
        "total_loan": total_price * p["initial_ltv"],
    }


def annual_irr(cash_flows):
    """Annual IRR of monthly cash flows, found by bisection on the monthly rate."""
    def npv(rate):
        total = 0.0
        discount = 1.0
        step = 1.0 / (1.0 + rate)
        for cf in cash_flows:
            total += cf * discount
            discount *= step
        return total

    low, high = -0.05, 0.05  # monthly rate bounds (about -46% to +80% a year)
    if npv(low) <= 0.0:
        monthly = low
    elif npv(high) >= 0.0:
        monthly = high
    else:
        for _ in range(60):
            mid = 0.5 * (low + high)
            if npv(mid) > 0.0:
                low = mid
            else:
                high = mid
        monthly = 0.5 * (low + high)
    return (1.0 + monthly) ** 12 - 1.0


def simulate_scenario(portfolio, scenario, seed):
    """Simulate one 10-year scenario. Returns (annual_irr, breached)."""
    p = PARAMS
    n = portfolio["n"]
    rent = portfolio["rent"]
    opex = portfolio["opex"]
    total_loan = portfolio["total_loan"]

    # All random numbers of the scenario, drawn up front from its own stream.
    rng = scenario_rng(seed, scenario)
    z_market = rng.standard_normal((MONTHS, 3)).tolist()   # rate, price, rent
    z_idio = rng.standard_normal((MONTHS, n)).tolist()     # per property
    u_vacancy = rng.random((MONTHS, n)).tolist()           # per property

    rate_speed, rate_mean = p["rate_speed"], p["rate_mean"]
    rate_step = p["rate_sigma"] * SQRT_DT
    rate_floor = p["rate_floor"]
    rent_drift, rent_step = p["rent_drift"] * DT, p["rent_sigma"] * SQRT_DT
    price_drift = p["price_drift"] * DT
    market_step = p["price_sigma_market"] * SQRT_DT
    idio_step = p["price_sigma_idio"] * SQRT_DT
    p_vacate, p_fill = p["p_vacate"], p["p_fill"]
    margin, covenant = p["margin"], p["covenant_ltv"]

    values = list(portfolio["price"])
    occupied = [True] * n
    rate = p["rate0"]
    rent_index = 1.0
    breached = False
    cash_flows = [-(portfolio["total_price"] - total_loan)]  # equity invested

    # Path-dependent loop: month t depends on month t-1 (values, vacancy, rate).
    for t in range(MONTHS):
        z_rate, z_price, z_rent = z_market[t]
        rate += rate_speed * (rate_mean - rate) * DT + rate_step * z_rate
        if rate < rate_floor:
            rate = rate_floor
        rent_index *= 1.0 + rent_drift + rent_step * z_rent
        market_growth = 1.0 + price_drift + market_step * z_price

        z_row = z_idio[t]
        u_row = u_vacancy[t]
        total_value = 0.0
        income = 0.0
        costs = 0.0
        for j in range(n):
            value = values[j] * (market_growth + idio_step * z_row[j])
            values[j] = value
            total_value += value
            if occupied[j]:
                if u_row[j] < p_vacate:
                    occupied[j] = False
            elif u_row[j] < p_fill:
                occupied[j] = True
            if occupied[j]:
                income += rent[j]
            costs += opex[j]

        interest = total_loan * (rate + margin) / 12.0
        cash_flow = (income - costs) * rent_index - interest
        if total_loan / total_value > covenant:
            breached = True
        if t == MONTHS - 1:  # sell the portfolio and repay the loan
            cash_flow += total_value * (1.0 - p["sale_cost"]) - total_loan
        cash_flows.append(cash_flow)

    return annual_irr(cash_flows), breached


def simulate_range(portfolio, start, stop, seed):
    """Simulate scenarios start..stop-1, in order. The unit of work of a worker."""
    return [simulate_scenario(portfolio, s, seed) for s in range(start, stop)]


def summarize(results):
    """Answer the analytical question from the per-scenario results."""
    irr = np.array([r[0] for r in results])
    breaches = sum(1 for r in results if r[1])
    return {
        "n_scenarios": len(results),
        "irr_p5": float(np.percentile(irr, 5)),
        "irr_median": float(np.median(irr)),
        "breach_count": breaches,
        "breach_probability": breaches / len(results),
    }
