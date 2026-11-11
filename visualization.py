"""
visualization.py
================
Section B(b) (3-panel publication figure) and Section A(c) (Matplotlib vs
Seaborn comparison charts) for the Smart Campus Energy & EV platform.

Every plotting helper draws onto a caller-supplied ``Axes`` so that the same
code serves both the static PNG export (this script) and the Streamlit app.

Modelling notes (the raw data has no solar or weather feed):
* Grid demand  = average energy (kWh) of sessions that START in an hour,
                 per day -> a kW-equivalent load proxy computed from real data.
* Solar curve  = SIMULATED half-sine PV profile (100 kWp, 07:00-19:00).
* Ambient temp = SIMULATED diurnal curve for a tropical campus (27-33 C).
"""

import logging
from typing import Optional

import matplotlib
matplotlib.use("Agg")                      # headless backend (no GUI needed)
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import seaborn as sns  # noqa: E402

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(message)s")

PV_PEAK_KW = 100.0                         # assumed installed solar capacity
PALETTE = {"AC": "#1f77b4", "DC": "#d62728"}
USER_ORDER = ["Student", "Staff", "Visitor"]

sns.set_theme(style="whitegrid", context="notebook")   # consistent look


# --------------------------------------------------------------------------- #
# Helper data builders
# --------------------------------------------------------------------------- #
def hourly_grid_demand(df: pd.DataFrame) -> pd.Series:
    """Average kWh drawn per hour-of-day per day (index 0..23)."""
    n_days = max(df["Session_Date"].nunique(), 1)
    return (df.groupby("Start_Hour")["Energy_kWh"].sum()
              .reindex(range(24), fill_value=0) / n_days)


def solar_profile() -> np.ndarray:
    """Simulated PV output (kW) for hours 0..23: half-sine from 07:00 to 19:00."""
    hours = np.arange(24)
    daylight = (hours >= 7) & (hours <= 19)
    return np.where(daylight, PV_PEAK_KW * np.sin(np.pi * (hours - 7) / 12), 0.0)


def ambient_profile() -> np.ndarray:
    """Simulated ambient temperature (deg C), coolest ~06:00, hottest ~15:00."""
    hours = np.arange(24)
    return 30.0 + 3.0 * np.sin(2 * np.pi * (hours - 9) / 24)


# --------------------------------------------------------------------------- #
# Section B(b): three panels
# --------------------------------------------------------------------------- #
def plot_grid_vs_solar(df: pd.DataFrame, ax: plt.Axes) -> None:
    """Panel 1 - hourly grid demand versus simulated solar generation."""
    demand = hourly_grid_demand(df)
    solar = solar_profile()
    ax.plot(demand.index, demand.values, marker="o", color="#d62728",
            label="Grid demand (kWh/h)")
    ax.plot(range(24), solar, marker="s", color="#ff9f1c",
            label="Solar generation (simulated, kW)")
    ax.fill_between(range(24), solar, color="#ff9f1c", alpha=0.15)
    peak_h = int(demand.idxmax())                       # busiest hour
    ax.annotate(f"Peak demand {demand.max():.0f} kWh\n@ {peak_h:02d}:00",
                xy=(peak_h, demand.max()),
                xytext=(peak_h + 1.5, demand.max() * 0.97),
                arrowprops=dict(arrowstyle="->"), fontsize=9)
    # head-room so that the legend and the peak note never collide with the lines
    ax.set_ylim(0, max(demand.max(), PV_PEAK_KW) * 1.4)
    ax.set_xticks(range(0, 24, 2))
    ax.set_xlabel("Hour of day")
    ax.set_ylabel("Energy / power")
    ax.set_title("Panel 1: Hourly grid demand vs solar generation")
    ax.legend(loc="upper right", fontsize=8)


def plot_cost_boxplot(df: pd.DataFrame, ax: plt.Axes) -> None:
    """Panel 2 - session cost distribution per user type (median annotated)."""
    sns.boxplot(data=df, x="User_Type", y="Net_Billable_MYR", order=USER_ORDER,
                hue="User_Type", palette="Set2", legend=False, ax=ax)
    medians = df.groupby("User_Type")["Net_Billable_MYR"].median()
    for i, user in enumerate(USER_ORDER):
        if user in medians:
            ax.text(i, medians[user], f"{medians[user]:.1f}", ha="center",
                    va="bottom", fontsize=9, fontweight="bold")
    ax.set_xlabel("User type")
    ax.set_ylabel("Net billable amount (MYR)")
    ax.set_title("Panel 2: Session cost by user type")


def plot_temp_vs_energy(df: pd.DataFrame, ax: plt.Axes) -> None:
    """Panel 3 - battery temperature vs energy delivered with trendlines."""
    sns.scatterplot(data=df, x="Battery_Temp_C", y="Energy_kWh",
                    hue="Charger_Type", palette=PALETTE, alpha=0.45, s=22, ax=ax)
    # one least-squares trendline per charger type + one overall (dashed)
    for ctype, sub in df.groupby("Charger_Type"):
        if len(sub) > 2:
            slope, icpt = np.polyfit(sub["Battery_Temp_C"], sub["Energy_kWh"], 1)
            t_lo, t_hi = sub["Battery_Temp_C"].min(), sub["Battery_Temp_C"].max()
            xs = np.linspace(t_lo, t_hi, 50)
            ax.plot(xs, slope * xs + icpt, color=PALETTE[ctype], lw=2)
    if len(df) > 2:
        slope, icpt = np.polyfit(df["Battery_Temp_C"], df["Energy_kWh"], 1)
        xs = np.linspace(df["Battery_Temp_C"].min(), df["Battery_Temp_C"].max(), 50)
        ax.plot(xs, slope * xs + icpt, "k--", lw=1.5, label="Overall trend")
        r = df["Battery_Temp_C"].corr(df["Energy_kWh"])
        ax.text(0.03, 0.95, f"Overall r = {r:.2f}", transform=ax.transAxes,
                va="top", fontsize=9, bbox=dict(boxstyle="round", fc="white"))
    ax.axvline(40, color="grey", ls=":", lw=1)          # alert temperature
    ax.set_xlabel("Battery temperature (deg C)")
    ax.set_ylabel("Energy delivered (kWh)")
    ax.set_title("Panel 3: Battery temperature vs energy")
    ax.legend(fontsize=8)


def build_three_panel_figure(df: pd.DataFrame) -> plt.Figure:
    """Compose Panels 1-3 into one publication-quality figure."""
    fig, axes = plt.subplots(1, 3, figsize=(18, 5.2))
    plot_grid_vs_solar(df, axes[0])
    plot_cost_boxplot(df, axes[1])
    plot_temp_vs_energy(df, axes[2])
    fig.tight_layout()
    return fig


# --------------------------------------------------------------------------- #
# Section A(c): Matplotlib vs Seaborn comparisons
# --------------------------------------------------------------------------- #
def hourly_revenue_table(df: pd.DataFrame) -> pd.DataFrame:
    """Pivot: rows = hour 0..23, columns = AC / DC, values = revenue (MYR)."""
    return (df.pivot_table(index="Start_Hour", columns="Charger_Type",
                           values="Net_Billable_MYR", aggfunc="sum", fill_value=0)
              .reindex(range(24), fill_value=0))


def multibar_matplotlib(df: pd.DataFrame, ax: plt.Axes) -> None:
    """Grouped bars drawn manually: the bar offsets are computed by hand."""
    tbl = hourly_revenue_table(df)
    x = np.arange(24)
    w = 0.4
    ax.bar(x - w / 2, tbl["AC"], w, label="AC", color=PALETTE["AC"])
    ax.bar(x + w / 2, tbl["DC"], w, label="DC", color=PALETTE["DC"])
    ax.set_xticks(x)
    ax.set_xlabel("Hour of day")
    ax.set_ylabel("Revenue (MYR)")
    ax.set_title("(a) Matplotlib - manual grouped bars")
    ax.legend(title="Charger")


def multibar_seaborn(df: pd.DataFrame, ax: plt.Axes) -> None:
    """Grouped bars in one call: seaborn handles dodging and the legend."""
    tbl = hourly_revenue_table(df).reset_index().melt(
        id_vars="Start_Hour", var_name="Charger_Type", value_name="Revenue")
    sns.barplot(data=tbl, x="Start_Hour", y="Revenue", hue="Charger_Type",
                palette=PALETTE, ax=ax)
    ax.set_xlabel("Hour of day")
    ax.set_ylabel("Revenue (MYR)")
    ax.set_title("(b) Seaborn - barplot(hue=...)")


def correlation_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Hourly table of ambient temperature, mean duration and grid load."""
    hourly = pd.DataFrame({
        "Ambient_Temp_C": ambient_profile(),
        "Duration_Mins": df.groupby("Start_Hour")["Duration_Mins"].mean()
                           .reindex(range(24)).values,
        "Grid_Load_kWh": hourly_grid_demand(df).values})
    return hourly.dropna()


def heatmap_matplotlib(df: pd.DataFrame, ax: plt.Axes) -> None:
    """Correlation heatmap with imshow + manual text annotations."""
    corr = correlation_frame(df).corr()
    im = ax.imshow(corr.values, cmap="coolwarm", vmin=-1, vmax=1)
    ax.set_xticks(range(len(corr)), corr.columns, rotation=20)
    ax.set_yticks(range(len(corr)), corr.columns)
    for i in range(len(corr)):                      # annotate every cell by hand
        for j in range(len(corr)):
            ax.text(j, i, f"{corr.values[i, j]:.2f}", ha="center", va="center")
    ax.figure.colorbar(im, ax=ax, fraction=0.046)
    ax.set_title("(a) Matplotlib - imshow")
    ax.grid(False)


def heatmap_seaborn(df: pd.DataFrame, ax: plt.Axes) -> None:
    """Correlation heatmap in a single seaborn call."""
    corr = correlation_frame(df).corr()
    sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm", vmin=-1, vmax=1,
                square=True, linewidths=0.5, ax=ax)
    ax.set_title("(b) Seaborn - heatmap(annot=True)")
    ax.tick_params(axis="x", rotation=20)


def save(fig: plt.Figure, path: str) -> None:
    """Save a figure at 200 dpi, logging success or failure."""
    try:
        fig.savefig(path, dpi=200, bbox_inches="tight")
        logging.info(f"Chart saved: {path}")
    except OSError as exc:
        logging.error(f"Could not save {path}: {exc}")
    finally:
        plt.close(fig)


def main(csv_path: str = "cleaned_energy_sales_data.csv",
         out_dir: Optional[str] = "charts") -> None:
    """Generate all static figures used in the report."""
    try:
        df = pd.read_csv(csv_path, parse_dates=["Session_Date"])
    except (FileNotFoundError, ValueError) as exc:
        logging.error(f"Cannot load cleaned data: {exc}")
        return
    logging.info(f"Cleaned data loaded: {len(df)} rows.")
    save(build_three_panel_figure(df), f"{out_dir}/fig_b_three_panels.png")

    fig, axes = plt.subplots(1, 2, figsize=(14, 4.8), sharey=True)
    multibar_matplotlib(df, axes[0])
    multibar_seaborn(df, axes[1])
    fig.tight_layout()
    save(fig, f"{out_dir}/fig_a_multibar.png")

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6))
    heatmap_matplotlib(df, axes[0])
    heatmap_seaborn(df, axes[1])
    fig.tight_layout()
    save(fig, f"{out_dir}/fig_a_heatmap.png")
    print(correlation_frame(df).corr().round(2))
    r = df.groupby("Charger_Type")[["Battery_Temp_C", "Energy_kWh"]].corr().round(3)
    print(r)


if __name__ == "__main__":
    main()
