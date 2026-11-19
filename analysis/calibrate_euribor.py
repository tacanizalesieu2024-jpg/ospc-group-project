import pandas as pd

# Load the Euribor dataset, skipping the first 8 metadata rows
euribor = pd.read_csv(
    "data/datos_madrid.csv",
    skiprows=8,
    header=None,
    names=["date", "rate"],
    encoding="utf-8-sig"
)

# Convert interest rates to numeric values
# Missing observations (-) become NaN
euribor["rate"] = pd.to_numeric(euribor["rate"], errors="coerce")

# Display the first observations
print(euribor.head(10))

# Check how many valid observations we have
print("\nValid observations:", euribor["rate"].notna().sum())

# Translate Spanish month abbreviations into numbers
months = {
    "ene": "01", "feb": "02", "mar": "03",
    "abr": "04", "may": "05", "jun": "06",
    "jul": "07", "ago": "08", "sep": "09",
    "oct": "10", "nov": "11", "dic": "12"
}

# Convert Spanish dates into YYYY-MM-DD format
euribor["month"] = euribor["date"].str[2:5].map(months)
euribor["day"] = euribor["date"].str[:2]
# Keep only rows with valid Spanish date formats
euribor = euribor[
    euribor["date"].astype(str).str.fullmatch(
        r"\d{2}(ene|feb|mar|abr|may|jun|jul|ago|sep|oct|nov|dic)\d{2}"
    )
].copy()

# Convert the last two digits into a year
euribor["year"] = euribor["date"].str[-2:].astype(int)

# Interpret two-digit years correctly
euribor["year"] = euribor["year"].apply(
    lambda y: 2000 + y if y <= 26 else 1900 + y
)

euribor["date_parsed"] = pd.to_datetime(
    euribor["year"].astype(str) + "-" +
    euribor["month"] + "-" + euribor["day"],
    errors="coerce"
)

# Select January 2015 to October 2026
euribor = euribor[
    (euribor["date_parsed"] >= "2015-01-01") &
    (euribor["date_parsed"] < "2026-11-01")
].copy()

# Calculate the average Euribor for each month
monthly = euribor.set_index("date_parsed")["rate"].resample("MS").mean()

# Convert percentages into decimal rates (3% = 0.03)
monthly = monthly / 100

# Display monthly data
print("\nMonthly Euribor (first 5 observations):")
print(monthly.head())

print("\nMonthly Euribor (last 5 observations):")
print(monthly.tail())

print("\nTotal months:", monthly.notna().sum())

# Calculate the historical average Euribor
rate_mean = monthly.mean()

# Use the latest complete month as the starting rate
rate0 = monthly.dropna().iloc[-1]

# Display calibrated parameters
print("\nEURIBOR CALIBRATION")
print("Historical average (rate_mean):", round(rate_mean * 100, 4), "%")
print("Starting rate (rate0):", round(rate0 * 100, 4), "%")

import numpy as np

# Remove months without valid data
rates = monthly.dropna()

# Previous month's interest rate
previous = rates.iloc[:-1].to_numpy()

# Change in interest rate from one month to the next
changes = np.diff(rates.to_numpy())

# Estimate: monthly change = intercept + slope * previous rate
slope, intercept = np.polyfit(previous, changes, 1)

# Convert monthly mean-reversion slope into annual parameter
rate_speed = -slope * 12

# Calculate unexplained monthly changes
residuals = changes - (intercept + slope * previous)

# Estimate annualized shock volatility
rate_sigma = np.std(residuals, ddof=2) * np.sqrt(12)

print("\nINTEREST RATE MODEL")
print("Estimated rate_speed:", round(rate_speed, 4))
print("Estimated rate_sigma:", round(rate_sigma, 6))

# Check the estimated monthly regression
print("\nREGRESSION CHECK")
print("Monthly slope:", round(slope, 6))
print("Monthly intercept:", round(intercept, 6))

# Calculate the long-run mean implied by the regression
if abs(slope) > 1e-10:
    implied_mean = -intercept / slope
    print("Implied long-run mean:", round(implied_mean * 100, 4), "%")
else:
    print("Long-run mean cannot be estimated reliably")
