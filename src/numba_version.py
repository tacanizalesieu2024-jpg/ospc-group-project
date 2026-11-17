import numpy as np
from numba import njit

from src.model import MONTHS, PARAMS, scenario_rng
@njit
def annual_irr_numba(cash_flows):
    """
    Calculate annual IRR using Numba.

    Uses the same bisection algorithm as the
    original annual_irr() function in model.py.
    """

    # Calculate Net Present Value for a monthly rate.
    # Numba compiles this numerical loop.
    low = -0.05
    high = 0.05

    # Calculate NPV at the lower bound.
    npv_low = 0.0
    discount = 1.0
    step = 1.0 / (1.0 + low)

    for cf in cash_flows:
        npv_low += cf * discount
        discount *= step

    # Calculate NPV at the upper bound.
    npv_high = 0.0
    discount = 1.0
    step = 1.0 / (1.0 + high)

    for cf in cash_flows:
        npv_high += cf * discount
        discount *= step

    if npv_low <= 0.0:
        monthly = low

    elif npv_high >= 0.0:
        monthly = high

    else:
        # Binary search for the monthly IRR.
        for _ in range(60):
            mid = 0.5 * (low + high)

            npv_mid = 0.0
            discount = 1.0
            step = 1.0 / (1.0 + mid)

            for cf in cash_flows:
                npv_mid += cf * discount
                discount *= step

            if npv_mid > 0.0:
                low = mid
            else:
                high = mid

        monthly = 0.5 * (low + high)

    # Convert monthly IRR to annual IRR.
    return (1.0 + monthly) ** 12 - 1.0



@njit
def simulate_core_numba(
    prices, rents, opex,
    total_price, total_loan,
    z_market, z_idio, u_vacancy,
    params
):
    """
    Simulate 120 months using Numba.

    Random numbers are generated outside this function
    to preserve the original Monte Carlo scenarios.
    """

    # Number of properties in the portfolio
    n = len(prices)

    # Copy initial property values so we do not
    # modify the original portfolio.
    values = prices.copy()

    # Initially, all properties are occupied.
    occupied = np.ones(n, dtype=np.bool_)

    # Initial financial conditions
    rate = params[0]
    rent_index = 1.0
    breached = False

    # Initial equity investment (negative cash flow)
    cash_flows = np.zeros(MONTHS + 1)
    cash_flows[0] = -(total_price - total_loan)


    # Financial parameters (same order as the original model)
    rate_speed = params[1]
    rate_mean = params[2]
    rate_step = params[3] * np.sqrt(1.0 / 12.0)
    rate_floor = params[4]

    rent_drift = params[5] / 12.0
    rent_step = params[6] * np.sqrt(1.0 / 12.0)

    price_drift = params[7] / 12.0
    market_step = params[8] * np.sqrt(1.0 / 12.0)
    idio_step = params[9] * np.sqrt(1.0 / 12.0)

    p_vacate = params[10]
    p_fill = params[11]
    margin = params[12]
    covenant = params[13]
    sale_cost = params[14]

    # Simulate the 120 months sequentially.
    # Each month depends on the previous month.
    for t in range(MONTHS):

        z_rate = z_market[t, 0]
        z_price = z_market[t, 1]
        z_rent = z_market[t, 2]

        # Update Euribor using the mean-reverting process.
        rate += rate_speed * (rate_mean - rate) / 12.0 + rate_step * z_rate

        if rate < rate_floor:
            rate = rate_floor

        # Update the rental income index.
        rent_index *= 1.0 + rent_drift + rent_step * z_rent

        # Market-wide property price change.
        market_growth = 1.0 + price_drift + market_step * z_price

        total_value = 0.0
        income = 0.0
        costs = 0.0

        # Update every property in the portfolio.
        for j in range(n):

            # Update property value.
            value = values[j] * (
                market_growth + idio_step * z_idio[t, j]
            )

            values[j] = value
            total_value += value

            # Update occupancy status.
            if occupied[j]:
                if u_vacancy[t, j] < p_vacate:
                    occupied[j] = False

            elif u_vacancy[t, j] < p_fill:
                occupied[j] = True

            # Add rent only if the property is occupied.
            if occupied[j]:
                income += rents[j]

            # Operating costs apply to every property.
            costs += opex[j]

        # Calculate monthly interest on the loan.
        interest = total_loan * (rate + margin) / 12.0

        # Calculate monthly cash flow.
        cash_flow = (income - costs) * rent_index - interest

        # Check whether the LTV covenant is breached.
        if total_loan / total_value > covenant:
            breached = True

        # At the end of year 10, sell the properties
        # and repay the outstanding loan.
        if t == MONTHS - 1:
            cash_flow += total_value * (1.0 - sale_cost) - total_loan

        cash_flows[t + 1] = cash_flow

    # Calculate annual IRR using our compiled function.
    return annual_irr_numba(cash_flows), breached


def simulate_scenario_numba(portfolio, scenario, seed):
    """
    Run one Monte Carlo scenario using Numba.

    Random draws and model parameters are identical
    to the original sequential implementation.
    """

    # Use the same independent random stream as model.py.
    rng = scenario_rng(seed, scenario)

    n = portfolio["n"]

    # Generate random numbers in exactly the same order.
    z_market = rng.standard_normal((MONTHS, 3))
    z_idio = rng.standard_normal((MONTHS, n))
    u_vacancy = rng.random((MONTHS, n))

    # Convert portfolio lists to numerical arrays.
    prices = np.asarray(portfolio["price"], dtype=np.float64)
    rents = np.asarray(portfolio["rent"], dtype=np.float64)
    opex = np.asarray(portfolio["opex"], dtype=np.float64)

    # Parameters in the exact order expected by simulate_core_numba.
    p = PARAMS

    params = np.array([
        p["rate0"],
        p["rate_speed"],
        p["rate_mean"],
        p["rate_sigma"],
        p["rate_floor"],
        p["rent_drift"],
        p["rent_sigma"],
        p["price_drift"],
        p["price_sigma_market"],
        p["price_sigma_idio"],
        p["p_vacate"],
        p["p_fill"],
        p["margin"],
        p["covenant_ltv"],
        p["sale_cost"],
    ], dtype=np.float64)

    # Execute the compiled numerical simulation.
    return simulate_core_numba(
        prices,
        rents,
        opex,
        portfolio["total_price"],
        portfolio["total_loan"],
        z_market,
        z_idio,
        u_vacancy,
        params,
    )
