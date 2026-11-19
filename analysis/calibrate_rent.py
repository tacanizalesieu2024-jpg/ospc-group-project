import pandas as pd

# Load rental price index data from INE
df = pd.read_csv(
    "data/indices_municipios.csv",
    sep=";",
    decimal=",",
    encoding="latin1"
)

# Keep only the year and rental index
rent = df[["Periodo", "Total"]].copy()

# Sort years from oldest to newest
rent = rent.sort_values("Periodo")

# Calculate annual rental price growth
rent["annual_growth"] = rent["Total"].pct_change()

# Calculate average annual growth
rent_drift = rent["annual_growth"].mean()

# Calculate annual rental volatility
rent_sigma = rent["annual_growth"].std()

# Calculate compound annual growth (CAGR)
first_index = rent["Total"].iloc[0]
last_index = rent["Total"].iloc[-1]
years = len(rent) - 1

rent_cagr = (last_index / first_index) ** (1 / years) - 1

# Display results
print("Period:", rent["Periodo"].iloc[0], "to", rent["Periodo"].iloc[-1])
print("Average annual rent growth:", round(rent_drift * 100, 2), "%")
print("Compound annual rent growth:", round(rent_cagr * 100, 2), "%")
print("Annual rent volatility:", round(rent_sigma * 100, 2), "%")
