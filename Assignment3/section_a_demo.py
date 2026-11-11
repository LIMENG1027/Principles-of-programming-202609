"""
section_a_demo.py
=================
Runnable code for Section A(a) (NumPy vs Pandas) and Section A(b) (functional
programming) of the ITS72604 Final Examination.

Input : cleaned_energy_sales_data.csv (produced by data_pipeline.py)
Run   : python section_a_demo.py
"""

import logging
import time
from functools import reduce
from typing import Dict, List

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(message)s")


# =========================================================================== #
# SECTION A(a) - NumPy and Pandas operations
# =========================================================================== #
def numpy_operations(df: pd.DataFrame) -> None:
    """Demonstrate two NumPy array operations on the telemetry."""
    # ---- NumPy op 1: 2-D array slicing --------------------------------------
    # Build a (days x 24) matrix of delivered kWh; row = day, column = hour.
    day_idx = (df["Session_Date"] - df["Session_Date"].min()).dt.days.to_numpy()
    load = np.zeros((day_idx.max() + 1, 24))
    # np.add.at accumulates correctly even when indices repeat (unbuffered add)
    np.add.at(load, (day_idx, df["Start_Hour"].to_numpy()), df["Energy_kWh"].to_numpy())
    peak_block = load[:, 8:18]                  # slice: 08:00-17:59 on all days
    print(f"[NumPy-1] Load matrix shape {load.shape}; peak-hour slice "
          f"{peak_block.shape}; mean peak-block load = {peak_block.mean():.1f} kWh/h")

    # ---- NumPy op 2: boolean masking ---------------------------------------
    temps = df["Battery_Temp_C"].to_numpy()
    mask = temps > 45.0                         # True where battery is too hot
    print(f"[NumPy-2] Sessions above 45 C: {mask.sum()} "
          f"(mean {temps[mask].mean():.1f} C, max {temps[mask].max():.1f} C)")


def pandas_operations(raw: pd.DataFrame, clean: pd.DataFrame) -> None:
    """Demonstrate two Pandas DataFrame operations."""
    # ---- Pandas op 1: median imputation (grouped by charger type) ----------
    filled = raw.copy()
    filled["Energy_kWh"] = filled["Energy_kWh"].fillna(
        filled.groupby("Charger_Type")["Energy_kWh"].transform("median"))
    print(f"[Pandas-1] Missing energy before={raw['Energy_kWh'].isna().sum()}, "
          f"after={filled['Energy_kWh'].isna().sum()}")
    # ---- Pandas op 2: group-wise charging revenue --------------------------
    revenue = clean.groupby("Charger_Type")["Net_Billable_MYR"].agg(["sum", "mean"])
    print("[Pandas-2] Revenue per charger type (MYR):\n", revenue.round(2))


def benchmark(n_rows: int = 1_000_000) -> None:
    """Time a Python-level loop against a vectorised NumPy/Pandas expression."""
    rng = np.random.default_rng(42)
    big = pd.DataFrame({"kwh": rng.uniform(3, 50, n_rows),
                        "hours": rng.uniform(0.25, 3.5, n_rows)})
    t0 = time.perf_counter()
    slow = [k / h for k, h in zip(big["kwh"], big["hours"])]   # per-row Python loop
    t_loop = time.perf_counter() - t0
    t0 = time.perf_counter()
    fast = big["kwh"].to_numpy() / big["hours"].to_numpy()     # vectorised C loop
    t_vec = time.perf_counter() - t0
    assert np.allclose(slow, fast)                             # identical results
    print(f"[Benchmark] {n_rows:,} rows: loop={t_loop:.3f}s, "
          f"vectorised={t_vec:.4f}s, speed-up x{t_loop / t_vec:.0f}")


# =========================================================================== #
# SECTION A(b) - functional programming pipeline
# =========================================================================== #
SURCHARGE = 0.15          # 15 % surcharge multiplier on the base energy fee


def is_high_risk(rec: Dict) -> bool:
    """Predicate: overstay > 20 minutes AND battery temperature > 40 deg C."""
    return rec["Overstay_Mins"] > 20 and rec["Battery_Temp_C"] > 40


def functional_pipeline(records: List[Dict]) -> float:
    """Filter -> map -> reduce over charging records, lazily evaluated.

    In Python 3, filter() and map() return ITERATORS: each record flows through
    the whole chain one at a time, so no intermediate list of the full data set
    is ever built (O(1) extra memory instead of O(n)).
    """
    # 1) FILTER - keep only high-risk sessions (named predicate, easy to test)
    risky = filter(is_high_risk, records)
    # 2) MAP - lambda returns a NEW dict (no mutation) with the 15 % surcharge
    #    on the base fee; **rec copies the original fields, then we add two keys.
    surcharged = map(lambda r: {**r,
                                "Surcharge_MYR": r["Base_Fee_MYR"] * SURCHARGE},
                     risky)
    # 3) REDUCE - fold the stream into one number; 0.0 is the initial value so
    #    an empty stream returns 0.0 instead of raising TypeError.
    total = reduce(lambda acc, r: acc + r["Surcharge_MYR"], surcharged, 0.0)
    return total


def comprehension_check(records: List[Dict]) -> float:
    """Independent cross-check using a generator expression + sum()."""
    return sum(r["Base_Fee_MYR"] * SURCHARGE for r in records if is_high_risk(r))


def main() -> None:
    """Load data, run Section A demonstrations and print the results."""
    try:
        clean = pd.read_csv("cleaned_energy_sales_data.csv", parse_dates=["Session_Date"])
        raw = pd.read_csv("ev_campus_dataset.csv")
        logging.info(f"Loaded {len(clean)} cleaned and {len(raw)} raw records.")
    except (FileNotFoundError, ValueError) as exc:
        logging.error(f"Input error: {exc}")
        return
    numpy_operations(clean)
    pandas_operations(raw, clean)
    benchmark()
    records = clean.to_dict("records")             # list of dicts
    n_alert = sum(1 for _ in filter(is_high_risk, records))
    total = functional_pipeline(records)
    print(f"[Functional] High-risk sessions: {n_alert}; total surcharge = "
          f"MYR {total:.4f}; cross-check = MYR {comprehension_check(records):.4f}")


if __name__ == "__main__":
    main()
