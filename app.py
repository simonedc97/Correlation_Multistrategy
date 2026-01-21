import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.colors import qualitative

# --------------------------------------------------
# Page config
# --------------------------------------------------
st.set_page_config(layout="wide")

# --------------------------------------------------
# Sidebar (common)
# --------------------------------------------------
st.sidebar.title("Controls")

chart_type = st.sidebar.selectbox(
    "Select chart",
    ["EGQ vs Index and Cash", "E7X vs Funds"]
)

# --------------------------------------------------
# Tabs
# --------------------------------------------------
tab_corr, tab_stress = st.tabs(["Correlation", "Stress Test"])

# --------------------------------------------------
# Load Correlation data
# --------------------------------------------------
@st.cache_data
def load_corr_data(path):
    df = pd.read_excel(path, sheet_name="Correlation Clean")
    df.iloc[:, 0] = pd.to_datetime(df.iloc[:, 0])
    df = df.set_index(df.columns[0]).sort_index()
    return df

corrEGQ = load_corr_data("corrEGQ.xlsx")
corrE7X = load_corr_data("corrE7X.xlsx")

# --------------------------------------------------
# Load Stress Test data
# --------------------------------------------------
@st.cache_data
def load_stress_data(path):
    xls = pd.ExcelFile(path)
    records = []

    for sheet in xls.sheet_names:
        if "_" in sheet:
            portfolio, scenario = sheet.split("_", 1)
        else:
            portfolio, scenario = sheet, sheet

        df = pd.read_excel(xls, sheet_name=sheet)

        df = df.rename(columns={
            df.columns[0]: "Date",
            df.columns[2]: "Scenario",
            df.columns[4]: "StressPnL"
        })

        df["Date"] = pd.to_datetime(df["Date"])
        df["Portfolio"] = portfolio
        df["ScenarioName"] = scenario

        records.append(
            df[["Date", "Scenario", "StressPnL", "Portfolio", "ScenarioName"]]
        )

    return pd.concat(records, ignore_index=True)

# ==================================================
# TAB — CORRELATION
# ==================================================
with tab_corr:
    st.title("Correlation Analysis")

    # Data selection
    if chart_type == "EGQ vs Index and Cash":
        df = corrEGQ.copy()
        chart_title = "EGQ vs Index and Cash"
    else:
        df = corrE7X.copy()
        chart_title = "E7X vs Funds"

    # -----------------------------
    # Sidebar controls (Correlation)
    # -----------------------------
    st.sidebar.subheader("Date range (Correlation)")

    start_date, end_date = st.sidebar.date_input(
        "Select start and end date",
        value=(df.index.min().date(), df.index.max().date()),
        min_value=df.index.min().date(),
        max_value=df.index.max().date()
    )

    df = df.loc[pd.to_datetime(start_date):pd.to_datetime(end_date)]

    st.sidebar.subheader("Series")

    selected_series = st.sidebar.multiselect(
        "Select series",
        options=df.columns.tolist(),
        default=df.columns.tolist()
    )

    if not selected_series:
        st.warning("Please select at least one series.")
        st.stop()

    # -----------------------------
    # Plot
    # -----------------------------
    palette = qualitative.Plotly
    color_map = {s: palette[i % len(palette)] for i, s in enumerate(selected_series)}

    st.subheader(chart_title)

    fig = go.Figure()

    for s in selected_series:
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df[s] * 100,
                mode="lines",
                name=s,
                line=dict(color=color_map[s]),
                hovertemplate="%{y:.2f}%<extra></extra>"
            )
        )

    fig.update_layout(
        template="plotly_white",
        hovermode="x unified",
        height=600,
        yaxis=dict(ticksuffix="%"),
        xaxis_title="Date",
        yaxis_title="Correlation"
    )

    st.plotly_chart(fig, use_container_width=True)

# ==================================================
# TAB — STRESS TEST
# ==================================================
with tab_stress:
    # File selection
    if chart_type == "EGQ vs Index and Cash":
        stress_path = "stress_test_totEGQ.xlsx"
        stress_title = "Stress Test Analysis – EGQ"
    else:
        stress_path = "stress_test_totE7X.xlsx"
        stress_title = "Stress Test Analysis – E7X"

    stress_data = load_stress_data(stress_path)

    st.title(stress_title)

    # -----------------------------
    # Sidebar controls (Stress Test)
    # -----------------------------
    st.sidebar.subheader("Date (Stress Test)")

    all_dates = sorted(stress_data["Date"].dropna().unique())
    date_str = st.sidebar.selectbox(
        "Select date",
        [d.strftime("%Y-%m-%d") for d in all_dates]
    )

    selected_date = pd.to_datetime(date_str)

    df_filtered = stress_data[
        stress_data["Date"] == selected_date
    ]

    st.sidebar.subheader("Portfolios")

    portfolios = sorted(df_filtered["Portfolio"].unique())
    selected_portfolios = st.sidebar.multiselect(
        "Select portfolios",
        portfolios,
        default=portfolios
    )

    st.sidebar.subheader("Scenarios")

    scenarios = sorted(df_filtered["ScenarioName"].unique())
    selected_scenarios = st.sidebar.multiselect(
        "Select scenarios",
        scenarios,
        default=scenarios
    )

    df_filtered = df_filtered[
        (df_filtered["Portfolio"].isin(selected_portfolios)) &
        (df_filtered["ScenarioName"].isin(selected_scenarios))
    ]

    if df_filtered.empty:
        st.warning("No data available for current selection.")
        st.stop()

    # -----------------------------
    # Stress PnL bar chart
    # -----------------------------
    st.subheader("Stress Test PnL")

    fig = go.Figure()
    palette = qualitative.Plotly

    for i, p in enumerate(selected_portfolios):
        df_p = df_filtered[df_filtered["Portfolio"] == p]
        if df_p.empty:
            continue

        fig.add_trace(
            go.Bar(
                x=df_p["ScenarioName"],
                y=df_p["StressPnL"],
                name=p,
                marker_color=palette[i % len(palette)]
            )
        )

    fig.update_layout(
        barmode="group",
        template="plotly_white",
        height=600,
        xaxis_title="Scenario",
        yaxis_title="Stress PnL (bps)"
    )

    st.plotly_chart(fig, use_container_width=True)

    # -----------------------------
    # Portfolio vs Peers
    # -----------------------------
    st.markdown("---")
    st.subheader("Portfolio vs Peers")

    selected_portfolio = st.selectbox(
        "Select portfolio",
        selected_portfolios
    )

    df_self = df_filtered[df_filtered["Portfolio"] == selected_portfolio]
    df_peers = df_filtered[df_filtered["Portfolio"] != selected_portfolio]

    if df_peers.empty:
        st.warning("Select at least two portfolios for comparison.")
        st.stop()

    stats = (
        df_peers
        .groupby("ScenarioName")
        .agg(
            median=("StressPnL", "median"),
            q25=("StressPnL", lambda x: x.quantile(0.25)),
            q75=("StressPnL", lambda x: x.quantile(0.75))
        )
        .reset_index()
    )

    df_plot = df_self.merge(stats, on="ScenarioName")

    fig = go.Figure()

    for _, r in df_plot.iterrows():
        fig.add_trace(
            go.Scatter(
                x=[r.q25, r.q75],
                y=[r.ScenarioName, r.ScenarioName],
                mode="lines",
                line=dict(width=14, color="rgba(255,0,0,0.25)"),
                showlegend=False
            )
        )

    fig.add_trace(
        go.Scatter(
            x=df_plot["median"],
            y=df_plot["ScenarioName"],
            mode="markers",
            name="Peer median",
            marker=dict(color="red", size=8)
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df_plot["StressPnL"],
            y=df_plot["ScenarioName"],
            mode="markers",
            name=selected_portfolio,
            marker=dict(symbol="star", size=14, color="orange")
        )
    )

    fig.update_layout(
        template="plotly_white",
        height=600,
        xaxis_title="Stress PnL (bps)",
        yaxis_title="Scenario"
    )

    st.plotly_chart(fig, use_container_width=True)
