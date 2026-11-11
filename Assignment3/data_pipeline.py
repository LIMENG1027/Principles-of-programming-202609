"""
data_pipeline.py
================
Section B(a) - Production-grade data pipeline for the Smart Campus Energy & EV
Fleet Management Platform (ITS72604 Final Examination, Sept 2026).

Pipeline stages
---------------
1. Load      : read ``ev_campus_dataset.csv`` (raw charging-session telemetry).
2. Cleanse   : validate categorical columns, remove physically impossible
               sensor values, impute missing numerics with GROUP-WISE medians.
3. Engineer  : Power Rate (kW), Carbon Savings (kg CO2), Net Billable Amount.
4. Export    : write ``cleaned_energy_sales_data.csv`` and print summary stats.

The module is import-safe: the Streamlit app and the visualisation module
re-use the pure functions below, and ``main()`` only runs when the file is
executed as a script (``python data_pipeline.py``).
"""

import logging
from pathlib import Path
from typing import Dict, Optional

import numpy as np
import pandas as pd

# --------------------------------------------------------------------------- #
# Logging: minimal, timestamped, level-tagged (industrial practice instead of
# scattering bare print() calls through the code base).
# --------------------------------------------------------------------------- #
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(message)s")

# --------------------------------------------------------------------------- #
# Business constants (single source of truth - change here, not in the logic)
# --------------------------------------------------------------------------- #
RAW_FILE = "ev_campus_dataset.csv"
CLEAN_FILE = "cleaned_energy_sales_data.csv"

CARBON_FACTOR_KG_PER_KWH = 0.475       # kg CO2 avoided per kWh (given in brief)
BASE_RATE_MYR_PER_HOUR: Dict[str, float] = {"AC": 6.0, "DC": 15.0}  # tariff
PEAK_HOURS = range(12, 18)             # 12:00-17:59 -> peak-surge window
PEAK_SURCHARGE_RATE = 0.25             # +25 % of base fee in peak window
OVERSTAY_GRACE_MINS = 15               # free grace period after charging ends
OVERSTAY_FEE_MYR_PER_MIN = 0.50        # penalty per minute beyond the grace
HIGH_RISK_OVERSTAY_MINS = 20           # alert rule: overstay  > 20 min ...
HIGH_RISK_TEMP_C = 40.0                # ... AND battery temp > 40 deg C

VALID_CHARGERS = {"AC", "DC"}
VALID_USERS = {"Student", "Staff", "Visitor"}
VALID_GRID = {"Normal", "Grid_Surge", "Overheated"}

# The raw file carries no timestamp, but Session_ID is strictly sequential, so
# sessions are spread evenly (60 per day) over the same 20-day window that is
# observed in sales_data.csv (2026-04-01 .. 2026-04-20). Documented assumption.
STUDY_START = pd.Timestamp("2026-04-01")
SESSIONS_PER_DAY = 60


def load_data(path: str = RAW_FILE) -> Optional[pd.DataFrame]:
    """Read the raw charging-session CSV file.

    Args:
        path: location of the CSV file.

    Returns:
        The raw DataFrame, or ``None`` if the file cannot be read.
    """
    try:
        df = pd.read_csv(path)
        logging.info(f"Dataset loaded successfully with {len(df)} records.")
        return df
    except FileNotFoundError:
        logging.error(f"Input file not found: {path}")
    except pd.errors.ParserError as exc:
        logging.error(f"Malformed CSV file {path}: {exc}")
    except Exception as exc:  # last-resort guard so the caller never crashes
        logging.error(f"Failed to load data: {exc}")
    return None


def validate_categoricals(df: pd.DataFrame) -> pd.DataFrame:
    """Normalise and validate the categorical columns.

    Leading/trailing blanks are stripped, then each column is compared with its
    whitelist of legal values; rows carrying an unknown label are dropped.
    """
    df = df.copy()
    rules = {"Charger_Type": VALID_CHARGERS,
             "User_Type": VALID_USERS,
             "Grid_Status_Label": VALID_GRID}
    before = len(df)
    for col, allowed in rules.items():
        df[col] = df[col].astype(str).str.strip()
        bad = ~df[col].isin(allowed)
        if bad.any():
            logging.warning(f"{col}: {bad.sum()} rows with unknown labels dropped.")
        df = df[~bad]
    logging.info(f"Categorical validation kept {len(df)}/{before} rows.")
    return df.reset_index(drop=True)


def remove_physical_noise(df: pd.DataFrame) -> pd.DataFrame:
    """Drop rows that violate basic physics (sensor noise).

    Battery temperatures below -20 C or above 100 C are impossible for a campus
    charger, as are non-positive energy / duration readings.  Already filtered
    out: sensor noise that contradicts physical common sense.
    """
    before = len(df)
    temp_ok = df["Battery_Temp_C"].between(-20, 100)      # keep -20 <= t <= 100
    energy_ok = df["Energy_kWh"].isna() | (df["Energy_kWh"] > 0)
    dur_ok = df["Duration_Mins"].isna() | (df["Duration_Mins"] > 0)
    df = df[temp_ok & energy_ok & dur_ok].reset_index(drop=True)
    logging.info(f"Physical validation removed {before - len(df)} noisy rows.")
    return df


def impute_group_median(df: pd.DataFrame, col: str,
                        group: str = "Charger_Type") -> pd.DataFrame:
    """Fill NaNs in ``col`` with the median of the row's own ``group``.

    AC and DC chargers deliver very different energy and have very different
    session lengths, so a single global median would bias both groups.
    """
    df = df.copy()
    n_missing = int(df[col].isna().sum())
    group_median = df.groupby(group)[col].transform("median")   # per-row median
    df[col] = df[col].fillna(group_median)
    df[col] = df[col].fillna(df[col].median())                  # safety net
    logging.info(f"{col}: imputed {n_missing} missing values (median by {group}).")
    return df


def add_session_date(df: pd.DataFrame) -> pd.DataFrame:
    """Attach a calendar date to each session (see STUDY_START note above)."""
    df = df.copy()
    day_offset = np.arange(len(df)) // SESSIONS_PER_DAY
    df["Session_Date"] = STUDY_START + pd.to_timedelta(day_offset, unit="D")
    return df


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Compute the derivative business metrics (vectorised, no Python loops)."""
    df = df.copy()
    df["Duration_Hours"] = df["Duration_Mins"] / 60.0
    # Power Rate (kW) = Energy (kWh) / Duration (h); clip avoids divide-by-zero
    df["Power_Rate_kW"] = df["Energy_kWh"] / df["Duration_Hours"].clip(lower=1 / 60)
    # Carbon Savings (kg CO2) = Energy x 0.475
    df["Carbon_Savings_kgCO2"] = df["Energy_kWh"] * CARBON_FACTOR_KG_PER_KWH
    # --- billing ---------------------------------------------------------- #
    df["Base_Rate_MYR"] = df["Charger_Type"].map(BASE_RATE_MYR_PER_HOUR)
    df["Base_Fee_MYR"] = df["Base_Rate_MYR"] * df["Duration_Hours"]
    in_peak = df["Start_Hour"].isin(PEAK_HOURS)
    df["Peak_Surge_MYR"] = np.where(in_peak,
                                    df["Base_Fee_MYR"] * PEAK_SURCHARGE_RATE, 0.0)
    billable_overstay = (df["Overstay_Mins"] - OVERSTAY_GRACE_MINS).clip(lower=0)
    df["Overstay_Fee_MYR"] = billable_overstay * OVERSTAY_FEE_MYR_PER_MIN
    df["Net_Billable_MYR"] = (df["Base_Fee_MYR"] + df["Peak_Surge_MYR"]
                              + df["Overstay_Fee_MYR"])
    # --- alert flag used by the dashboard and Section A(b) ------------------ #
    df["High_Risk_Flag"] = ((df["Overstay_Mins"] > HIGH_RISK_OVERSTAY_MINS)
                            & (df["Battery_Temp_C"] > HIGH_RISK_TEMP_C))
    # round only numeric columns (Session_Date is datetime and must be left alone)
    num_cols = df.select_dtypes(include="number").columns
    df[num_cols] = df[num_cols].round(4)
    return df


def clean_pipeline(raw: pd.DataFrame) -> pd.DataFrame:
    """Run every cleansing + feature-engineering step in the correct order."""
    df = validate_categoricals(raw)
    df = remove_physical_noise(df)
    for col in ("Energy_kWh", "Duration_Mins"):
        df = impute_group_median(df, col)
    df = add_session_date(df)
    return engineer_features(df)


def export_clean(df: pd.DataFrame, path: str = CLEAN_FILE) -> bool:
    """Persist the cleaned dataset; returns True on success."""
    try:
        df.to_csv(path, index=False)
        logging.info(f"Cleaned dataset exported to {Path(path).resolve().name}.")
        return True
    except OSError as exc:
        logging.error(f"Could not write {path}: {exc}")
        return False


def print_summary(df: pd.DataFrame) -> None:
    """Show summary statistics in the execution console."""
    pd.set_option("display.width", 160, "display.max_columns", 30)
    num_cols = ["Duration_Mins", "Energy_kWh", "Battery_Temp_C", "Power_Rate_kW",
                "Carbon_Savings_kgCO2", "Net_Billable_MYR"]
    print("\n=== SUMMARY STATISTICS (numeric) ===")
    print(df[num_cols].describe().round(2).T)
    print("\n=== REVENUE & ENERGY BY CHARGER TYPE ===")
    print(df.groupby("Charger_Type").agg(Sessions=("Session_ID", "count"),
          Energy_kWh=("Energy_kWh", "sum"), Revenue_MYR=("Net_Billable_MYR", "sum"),
          Avg_kW=("Power_Rate_kW", "mean")).round(2))
    print(f"\nHigh-risk sessions (overstay>{HIGH_RISK_OVERSTAY_MINS} min AND "
          f"temp>{HIGH_RISK_TEMP_C:.0f} C): {int(df['High_Risk_Flag'].sum())}")
    print(f"Missing values remaining: {int(df.isna().sum().sum())}")


def main() -> None:
    """Script entry point: load -> clean -> export -> summarise."""
    raw = load_data(RAW_FILE)
    if raw is None:
        return
    print("Missing values BEFORE cleaning:\n", raw.isna().sum()[raw.isna().sum() > 0])
    clean = clean_pipeline(raw)
    export_clean(clean)
    print_summary(clean)


if __name__ == "__main__":
    main()
