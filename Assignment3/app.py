"""
app.py - Smart Campus Energy & EV Fleet Dashboard (Section B(c)).

Run with:  streamlit run app.py

Pages (sidebar navigation): Executive Overview | Visual Analytics |
Alert Center | Data Explorer.  The sidebar filters (date range, minimum energy,
charger type) drive every page in real time.
"""

import logging
from typing import Optional, Tuple

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

import data_pipeline as dp          # cleansing + feature engineering
import visualization as viz         # plotting helpers (draw onto an Axes)

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(message)s")
st.set_page_config(page_title="Smart Campus EV Energy Hub", page_icon="⚡",
                   layout="wide")


# --------------------------------------------------------------------------- #
# Cached data layer
# --------------------------------------------------------------------------- #
@st.cache_data  # use the cache mechanism to avoid repeated I/O on UI interaction
def load_raw(path: str = dp.RAW_FILE) -> Optional[pd.DataFrame]:
    """Read the raw CSV once; later reruns are served from memory."""
    return dp.load_data(path)


@st.cache_data  # cached cleansing: only recomputed if the raw input changes
def get_clean_data(path: str = dp.RAW_FILE) -> Optional[pd.DataFrame]:
    """Load + clean + engineer features (cached)."""
    raw = load_raw(path)
    return None if raw is None else dp.clean_pipeline(raw)


# --------------------------------------------------------------------------- #
# Helper functions
# --------------------------------------------------------------------------- #
def apply_filters(df: pd.DataFrame) -> pd.DataFrame:
    """Render the sidebar widgets and return the filtered DataFrame."""
    st.sidebar.header("Filters")
    d_min, d_max = df["Session_Date"].min().date(), df["Session_Date"].max().date()
    picked = st.sidebar.date_input("Date range", (d_min, d_max),
                                   min_value=d_min, max_value=d_max)
    # date_input returns a 1-tuple while the user is still choosing the end date
    start, end = (picked[0], picked[-1]) if len(picked) else (d_min, d_max)
    min_kwh = st.sidebar.slider("Minimum energy (kWh)", 0.0,
                                float(df["Energy_kWh"].max()), 0.0, 0.5)
    chargers = st.sidebar.multiselect("Charger type", ["AC", "DC"],
                                      default=["AC", "DC"])
    mask = (df["Session_Date"].dt.date.between(start, end)
            & (df["Energy_kWh"] >= min_kwh)
            & df["Charger_Type"].isin(chargers))
    return df[mask].copy()


def high_risk(df: pd.DataFrame, temp_thr: float, overstay_thr: int) -> pd.DataFrame:
    """Sessions whose overstay and battery temperature both exceed thresholds."""
    return df[(df["Overstay_Mins"] > overstay_thr) & (df["Battery_Temp_C"] > temp_thr)]


def pct_vs_baseline(value: float, per_day_all: float, n_days: int) -> str:
    """Delta label: filtered daily average versus the whole-dataset daily average."""
    base = per_day_all
    now = value / max(n_days, 1)
    return f"{(now - base) / base * 100:+.1f}% vs daily avg" if base else "n/a"


def alert_banner(risky: pd.DataFrame) -> None:
    """Dynamic management alert shown at the top of every page."""
    n = len(risky)
    if n > 5:   # large-scale risk -> management-level red banner
        st.error("⚠️ WARNING: Large-scale grid overload risk detected - "
                 "restrict DC charger power immediately!")
    elif n > 0:
        st.warning(f"{n} high-risk session(s) detected - monitor closely.")
    else:
        st.success("No high-risk sessions under the current filters.")


def fig_one(plot_fn, df: pd.DataFrame, size: Tuple[int, int] = (7, 4.5)):
    """Create a single-axes figure, draw with ``plot_fn`` and return it."""
    fig, ax = plt.subplots(figsize=size)
    plot_fn(df, ax)
    fig.tight_layout()
    return fig


# --------------------------------------------------------------------------- #
# Pages
# --------------------------------------------------------------------------- #
def page_overview(df: pd.DataFrame, full: pd.DataFrame, risky: pd.DataFrame) -> None:
    """Executive KPI header (st.metric with deltas) and two summary charts."""
    n_days_f = df["Session_Date"].nunique()
    n_days_a = full["Session_Date"].nunique()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Energy Delivered", f"{df['Energy_kWh'].sum():,.0f} kWh",
              pct_vs_baseline(df["Energy_kWh"].sum(),
                              full["Energy_kWh"].sum() / n_days_a, n_days_f))
    c2.metric("Carbon Offset", f"{df['Carbon_Savings_kgCO2'].sum():,.0f} kg CO2",
              pct_vs_baseline(df["Carbon_Savings_kgCO2"].sum(),
                              full["Carbon_Savings_kgCO2"].sum() / n_days_a, n_days_f))
    c3.metric("Total Revenue", f"MYR {df['Net_Billable_MYR'].sum():,.0f}",
              pct_vs_baseline(df["Net_Billable_MYR"].sum(),
                              full["Net_Billable_MYR"].sum() / n_days_a, n_days_f))
    c4.metric("Active Alert Count", f"{len(risky)}", f"{len(risky)} sessions",
              delta_color="inverse")      # red when alerts rise
    left, right = st.columns(2)
    with left:
        fig = fig_one(viz.multibar_seaborn, df)
        fig.axes[0].set_title("Hourly charging revenue by charger type")  # dashboard title
        st.pyplot(fig)
    with right:
        st.pyplot(fig_one(viz.plot_grid_vs_solar, df))


def page_analytics(df: pd.DataFrame) -> None:
    """The three publication-quality panels of Section B(b)."""
    st.pyplot(viz.build_three_panel_figure(df))


def page_alerts(df: pd.DataFrame) -> pd.DataFrame:
    """Alert Center: custom thresholds + banners + high-risk table."""
    c1, c2 = st.columns(2)
    temp_thr = c1.slider("Battery temperature threshold (deg C)", 30, 55,
                         int(dp.HIGH_RISK_TEMP_C), key="temp_thr")
    over_thr = c2.slider("Overstay threshold (minutes)", 0, 60,
                         dp.HIGH_RISK_OVERSTAY_MINS, key="over_thr")
    risky = high_risk(df, temp_thr, over_thr)
    alert_banner(risky)
    if len(risky) > 0:
        st.warning(f"{len(risky)} sessions exceed {temp_thr} C and {over_thr} min overstay; "
                   f"DC share = {(risky['Charger_Type'] == 'DC').mean():.0%}.")
        st.dataframe(risky.sort_values("Battery_Temp_C", ascending=False)[
            ["Session_ID", "Charger_Type", "User_Type", "Start_Hour", "Overstay_Mins",
             "Battery_Temp_C", "Grid_Status_Label", "Net_Billable_MYR"]],
            width="stretch")
    return risky


def page_data(df: pd.DataFrame) -> None:
    """Filtered data viewer and CSV download button."""
    st.write(f"{len(df):,} sessions match the current filters.")
    st.dataframe(df, width="stretch")
    st.download_button("Download filtered data (CSV)",
                       df.to_csv(index=False).encode("utf-8"),
                       file_name="filtered_ev_sessions.csv", mime="text/csv")


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> None:
    """Assemble the app: data -> filters -> alert banner -> selected page."""
    st.title("⚡ Smart Campus Energy & EV Fleet Management")
    full = get_clean_data()
    if full is None or full.empty:
        st.error(f"Could not load {dp.RAW_FILE}. Place it next to app.py.")
        return
    page = st.sidebar.radio("Navigation", ["Executive Overview", "Visual Analytics",
                                           "Alert Center", "Data Explorer"])
    df = apply_filters(full)
    if df.empty:
        st.info("No sessions match the filters - widen the date range or charger type.")
        return
    # banner uses thresholds stored by the Alert Center sliders (defaults otherwise)
    risky = high_risk(df, st.session_state.get("temp_thr", dp.HIGH_RISK_TEMP_C),
                      st.session_state.get("over_thr", dp.HIGH_RISK_OVERSTAY_MINS))
    if page != "Alert Center":
        alert_banner(risky)          # Alert Center renders its own banner
    if page == "Executive Overview":
        page_overview(df, full, risky)
    elif page == "Visual Analytics":
        page_analytics(df)
    elif page == "Alert Center":
        page_alerts(df)
    else:
        page_data(df)


if __name__ == "__main__":
    main()
