import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.colors import qualitative
from io import BytesIO

# --------------------------------------------------
# Page config
# --------------------------------------------------
st.set_page_config(layout="wide")

# --------------------------------------------------
# Sidebar – GLOBAL CONTROLS
# --------------------------------------------------
with st.sidebar:
    st.title("Controls")

    chart_type = st.selectbox(
        "Select chart",
        ["EGQ vs Index and Cash", "E7X vs Funds"]
    )

# --------------------------------------------------
# Tabs
# --------------------------------------------------
tab_corr, tab_stress, tab_exposure, tab_legenda = st.tabs(
    ["Correlation", "Stress Test", "Exposure", "Legend"]
)

# --------------------------------------------------
# Data loaders
# --------------------------------------------------
@st.cache_data
def load_corr_data(path):
    df = pd.read_excel(path, sheet_name="Correlation Clean")
    df.iloc[:, 0] = pd.to_datetime(df.iloc[:, 0])
    return df.set_index(df.columns[0]).sort_index()


@st.cache_data
def load_stress_data(path):
    xls = pd.ExcelFile(path)
    records = []

    for sheet in xls.sheet_names:
        if "&&" in sheet:
            portfolio, scenario = sheet.split("&&", 1)
        else:
            portfolio = scenario = sheet

        df = pd.read_excel(xls, sheet_name=sheet)
        df = df.rename(columns={
            df.columns[0]: "Date",
            df.columns[2]: "Scenario",
            df.columns[4]: "StressPnL"
        })
        df["Date"] = pd.to_datetime(df["Date"])
        df["Portfolio"] = portfolio
        df["ScenarioName"] = scenario

        records.append(df[[
            "Date", "Scenario", "StressPnL", "Portfolio", "ScenarioName"
        ]])

    return pd.concat(records, ignore_index=True)


@st.cache_data
def load_exposure_data(path):
    df = pd.read_excel(path, sheet_name="MeasuresSeries")
    df = df.rename(columns={
        df.columns[0]: "Date",
        df.columns[3]: "Portfolio",
        df.columns[4]: "Equity Exposure",
        df.columns[5]: "Duration",
        df.columns[6]: "Spread Duration"
    })
    df["Date"] = pd.to_datetime(df["Date"])
    df.columns = df.columns.str.strip()
    return df


@st.cache_data
def load_legenda_sheet(sheet_name, usecols):
    return pd.read_excel("Legenda.xlsx", sheet_name=sheet_name, usecols=usecols)


# --------------------------------------------------
# Load data
# --------------------------------------------------
corrEGQ = load_corr_data("corrEGQ.xlsx")
corrE7X = load_corr_data("corrE7X.xlsx")

exposure_data = load_exposure_data("E7X_Exposure.xlsx")

stress_path = (
    "stress_test_totEGQ.xlsx"
    if chart_type == "EGQ vs Index and Cash"
    else "stress_test_totE7X.xlsx"
)
stress_data = load_stress_data(stress_path)

# ==================================================
# TAB — CORRELATION
# ==================================================
with tab_corr:
    st.title(
        "EGQ Flexible Multistrategy vs Index and Cash"
        if chart_type == "EGQ vs Index and Cash"
        else "E7X Dynamic Asset Allocation vs Funds"
    )

    df = corrEGQ.copy() if chart_type == "EGQ vs Index and Cash" else corrE7X.copy()

    # Sidebar (Correlation only)
    with st.sidebar:
        st.subheader("Date range (Correlation)")
        start_date, end_date = st.date_input(
            "Select start and end date",
            value=(df.index.min().date(), df.index.max().date())
        )

        st.subheader("Series (Correlation)")
        selected_series = st.multiselect(
            "Select series",
            options=df.columns.tolist(),
            default=df.columns.tolist()
        )

    if not selected_series:
        st.warning("Please select at least one series.")
        st.stop()

    df = df.loc[pd.to_datetime(start_date):pd.to_datetime(end_date)]

    # Plot
    fig = go.Figure()
    palette = qualitative.Plotly

    for i, col in enumerate(selected_series):
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df[col] * 100,
                name=col,
                line=dict(color=palette[i % len(palette)])
            )
        )

    fig.update_layout(
        template="plotly_white",
        hovermode="x unified",
        yaxis=dict(ticksuffix="%"),
        height=600
    )

    st.plotly_chart(fig, use_container_width=True)

# ==================================================
# TAB — STRESS TEST
# ==================================================
with tab_stress:
    st.title(
        "EGQ Flexible Multistrategy vs Index"
        if chart_type == "EGQ vs Index and Cash"
        else "E7X Dynamic Asset Allocation vs Funds"
    )

    with st.sidebar:
        st.subheader("Date (Stress Test)")
        dates = sorted(stress_data["Date"].dropna().unique())
        date_str = st.selectbox(
            "Select date",
            [d.strftime("%Y/%m/%d") for d in dates]
        )

        selected_date = pd.to_datetime(date_str)

        st.subheader("Series (Stress Test)")
        portfolios = stress_data["Portfolio"].unique().tolist()
        selected_portfolios = st.multiselect(
            "Select series",
            portfolios,
            default=portfolios
        )

        st.subheader("Scenarios (Stress Test)")
        scenarios = stress_data["ScenarioName"].unique().tolist()
        selected_scenarios = st.multiselect(
            "Select scenarios",
            scenarios,
            default=scenarios
        )

    df = stress_data[
        (stress_data["Date"] == selected_date) &
        (stress_data["Portfolio"].isin(selected_portfolios)) &
        (stress_data["ScenarioName"].isin(selected_scenarios))
    ]

    if df.empty:
        st.warning("No data available.")
        st.stop()

    fig = go.Figure()
    palette = qualitative.Plotly

    for i, p in enumerate(selected_portfolios):
        d = df[df["Portfolio"] == p]
        fig.add_trace(
            go.Bar(
                x=d["ScenarioName"],
                y=d["StressPnL"],
                name=p,
                marker_color=palette[i % len(palette)]
            )
        )

    fig.update_layout(
        barmode="group",
        template="plotly_white",
        height=600,
        yaxis_title="Stress PnL (bps)"
    )

    st.plotly_chart(fig, use_container_width=True)

# ==================================================
# TAB — EXPOSURE
# ==================================================
with tab_exposure:
    st.title(
        "E7X Dynamic Asset Allocation vs Funds"
        if chart_type == "E7X vs Funds"
        else "EGQ Flexible Multistrategy vs Index and Cash"
    )

    if chart_type != "E7X vs Funds":
        st.info("Analysis not performed for this subset.")
        st.stop()

    with st.sidebar:
        st.subheader("Date (Exposure)")
        dates = sorted(exposure_data["Date"].unique())
        date_str = st.selectbox(
            "Select date",
            [d.strftime("%Y/%m/%d") for d in dates],
            index=len(dates) - 1
        )

        selected_date = pd.to_datetime(date_str)

        st.subheader("Series (Exposure)")
        portfolios = exposure_data["Portfolio"].unique().tolist()
        selected_portfolios = st.multiselect(
            "Select portfolios",
            portfolios,
            default=portfolios
        )

    df = exposure_data[
        (exposure_data["Date"] == selected_date) &
        (exposure_data["Portfolio"].isin(selected_portfolios))
    ]

    metrics = ["Equity Exposure", "Duration", "Spread Duration"]

    df_plot = df.melt(
        id_vars="Portfolio",
        value_vars=metrics,
        var_name="Metric",
        value_name="Value"
    )

    fig = go.Figure()
    palette = qualitative.Plotly

    for i, p in enumerate(selected_portfolios):
        d = df_plot[df_plot["Portfolio"] == p]
        fig.add_trace(
            go.Bar(
                x=d["Metric"],
                y=d["Value"],
                name=p,
                marker_color=palette[i % len(palette)]
            )
        )

    fig.update_layout(
        barmode="group",
        template="plotly_white",
        height=600
    )

    st.plotly_chart(fig, use_container_width=True)

# ==================================================
# TAB — LEGENDA
# ==================================================
with tab_legenda:
    st.title(
        "EGQ Flexible Multistrategy vs Index and Cash"
        if chart_type == "EGQ vs Index and Cash"
        else "E7X Dynamic Asset Allocation vs Funds"
    )

    sheet = "EGQ" if chart_type == "EGQ vs Index and Cash" else "E7X"

    legenda_main = load_legenda_sheet(sheet, "A:C")
    st.subheader("Series")
    st.dataframe(legenda_main, use_container_width=True, hide_index=True)

    st.markdown("---")

    legenda_scenari = load_legenda_sheet("Scenari", "A:B")
    st.subheader("Stress Test Scenarios")
    st.dataframe(legenda_scenari, use_container_width=True, hide_index=True)
