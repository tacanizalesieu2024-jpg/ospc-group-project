# Monte Carlo risk of a Madrid rental property portfolio

Operating Systems and Parallel Computing, group project.

**Question:** for a fund holding 500 Madrid rental properties financed with
floating-rate debt, what is the 5th-percentile 10-year IRR, and what is the
probability that the loan-to-value (LTV) covenant is breached at least once?

**Team:** 

## Layout

| Path | Content |
|---|---|
| `src/model.py` | Shared model: portfolio, random streams, one-scenario simulation |
| `src/common.py` | Command line, timing and CSV logging shared by all versions |
| `src/sequential.py` | Sequential baseline |
| `src/pool.py` | Process-pool version (`multiprocessing.Pool`) |
| `tests/check_equivalence.py` | Automated check: parallel results = sequential results |
| `jobs/` | Slurm job scripts |
| `results/` | Raw timings, one CSV row per run |
| `analysis/plot_scaling.py` | Builds the scaling table and plot from the CSVs |

## Run on the cluster

Open a terminal in JupyterLab (https://jupyter.iesci.tech:8085), then:

```bash
git clone <URL of this repository>
cd <repository folder>
export PATH=/data/software/envs/ospc/bin:$PATH
```

### Small configuration (under five minutes)

```bash
python tests/check_equivalence.py
python src/sequential.py --scenarios 200
python src/pool.py --scenarios 200 --workers 2
```

Both versions must print the same 5th-percentile IRR and the same breach count.

### Measurements (batch jobs)

Problem size = number of scenarios (`SCENARIOS`). Each job runs 5 repetitions.

```bash
# Sequential baseline
sbatch --export=ALL,SCENARIOS=10000 jobs/sequential.sh

# Strong scaling of the pool: 1, 2, 4, 8, 16, 32 workers (2 CPUs = 1 physical core)
for cpus in 2 4 8 16 32 64; do
    sbatch --cpus-per-task=$cpus --export=ALL,SCENARIOS=10000 jobs/pool.sh
done

squeue -u $USER          # R = running, PD = waiting
```

The 64-CPU job only starts when the JupyterLab session is stopped, because the
session uses 2 of the 64 CPUs of the account.

### Table and plot

```bash
python analysis/plot_scaling.py --scenarios 10000
```

Writes `results/scaling.png` and prints run time, speedup and efficiency.

## Reproducibility

- Every scenario has its own random stream, derived from `(seed, scenario index)`
  with NumPy's `SeedSequence`. Results do not depend on the number of workers,
  the chunk size, or the order in which workers finish.
- Each run records node, Slurm job ID, node load and date in its CSV row.

## Use of generative AI

## Model Input Calibration

The financial model was calibrated using historical data for Madrid housing prices, rental prices, and the 12-month Euribor. Historical estimates replace illustrative values, while parameters without sufficient data remain documented assumptions.

### Calibrated parameters

| Parameter | Value | Source / Method |
|---|---:|---|
| price_drift | 0.0781 | INE IPV, CAGR (2015Q1–2026Q2) |
| price_sigma_market | 0.0326 | INE IPV, annualized quarterly volatility |
| price_sigma_idio | 0.0800 | Assumption: property-specific volatility |
| rent_drift | 0.0229 | INE IPVA Madrid, CAGR (2015–2024) |
| rent_sigma | 0.0127 | INE IPVA, standard deviation of annual growth |
| yield_low | 0.0400 | Assumed lower bound |
| yield_high | 0.0540 | Assumed upper bound |
| rate0 | 0.032386 | Banco de España, October 2026 monthly average |
| rate_mean | 0.009771 | Banco de España, 2015–October 2026 average |
| rate_sigma | 0.004949 | Monthly Euribor regression residuals, annualized |
| rate_speed | 0.3000 | Retained mean-reversion assumption |
| p_vacate | 0.020833 | Assumed average tenancy of 48 months |
| p_fill | 1.0000 | Assumed re-occupation in the next available month |

The rental yield interval has a midpoint of 4.7%, consistent with the Madrid residential gross rental yield reported by Idealista for Q4 2025.

### Data sources and periods

- INE, Housing Price Index (IPV), Comunidad de Madrid, quarterly data, 2015Q1–2026Q2, base 2025.
- INE, Experimental Rental Housing Price Index (IPVA), Madrid municipality, annual data, 2015–2024, base 2015.
- Banco de España, 12-month Euribor, series D_DNBAF172, daily observations aggregated to monthly averages, January 2015–October 2026.
- Idealista, residential gross rental yield, Madrid capital, Q4 2025.

### Methods and conversions

Housing price growth was estimated using the compound annual growth rate (CAGR). Market volatility was estimated as the standard deviation of quarterly growth multiplied by the square root of four.

Rental growth was estimated using CAGR, while rental volatility was calculated as the standard deviation of annual growth rates.

Daily Euribor observations were averaged by month and converted from percentages to decimal rates. Interest-rate volatility was estimated from monthly regression residuals and annualized using the square root of twelve.

The simulation converts annual growth rates into monthly inputs. Annual volatility coefficients are converted using the square root of twelve. Vacancy transition probabilities are already monthly.

### Assumptions and limitations

- Historical growth and volatility do not guarantee future performance.
- Regional housing price data are used as a proxy for Madrid city.
- The IPVA is an experimental annual statistic with a limited sample of years.
- The regional housing price index does not measure individual property volatility; price_sigma_idio remains an assumption.
- The rental yield bounds are assumed around the published 4.7% midpoint.
- Vacancy parameters are assumptions rather than direct estimates from observed tenant transitions.
- Euribor regression produced a negative mean-reversion estimate (-0.032). Therefore, rate_speed = 0.30 is retained as an illustrative assumption rather than an empirically calibrated value.
- The historical Euribor average is not a forecast of its future equilibrium.

### Validation

The calibrated parameters were applied to src/model.py.

The equivalence test was executed using:

    python tests/check_equivalence.py

Result: ALL CHECKS PASSED.

