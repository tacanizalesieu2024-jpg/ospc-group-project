import pandas as pd

# Load housing price data from INE
df = pd.read_csv(
    "data/79563.csv",
    sep=";",
    decimal=",",
    encoding="latin1"
)

# Keep only the period and housing price index
prices = df[["Periodo", "Total"]].copy()

# Sort quarters from oldest to newest
prices = prices.sort_values("Periodo")

# Calculate quarterly growth
prices["quarterly_growth"] = prices["Total"].pct_change()

# Calculate average quarterly growth
avg_quarterly_growth = prices["quarterly_growth"].mean()

# Convert quarterly growth into annual growth
price_drift = (1 + avg_quarterly_growth) ** 4 - 1

# Calculate quarterly volatility
quarterly_volatility = prices["quarterly_growth"].std()

# Annualize volatility
price_sigma_market = quarterly_volatility * (4 ** 0.5)

# Display results
print("Period:", prices["Periodo"].iloc[0], "to", prices["Periodo"].iloc[-1])
print("Average quarterly growth:", round(avg_quarterly_growth * 100, 2), "%")
print("Annual price growth:", round(price_drift * 100, 2), "%")
print("Quarterly volatility:", round(quarterly_volatility * 100, 2), "%")
print("Annual market volatility:", round(price_sigma_market * 100, 2), "%")

# Calculate compound annual growth rate (CAGR)
first_index = prices["Total"].iloc[0]
last_index = prices["Total"].iloc[-1]

# Number of years between first and last quarter
years = (len(prices) - 1) / 4

cagr = (last_index / first_index) ** (1 / years) - 1

print("Compound annual growth (CAGR):", round(cagr * 100, 2), "%")
