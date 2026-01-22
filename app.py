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
# Tabs
# --------------------------------------------------
tab_corr, tab_stress = st.tabs(["Correlation", "Stress Test"])

# --------------------------------------------------
# Sidebar controls
# --------------------------------------------------
st.sidebar.title("Controls")

chart_type = st.sidebar.selectbox(
    "Select chart",
    ["EGQ vs Index and Cash", "E7X vs Funds"]
)

# ==================================================
# CORRELATION — DATA
# ==================================================
@st.cache_data
def load_corr_data(path):
    df = pd.read_excel(path, sheet_name="Correlation Clean")
    df.iloc[:, 0] = pd.to_datetime(df.iloc[:, 0])
    return df.set_index(df.columns[0]).sort_index()


corrEGQ = load_corr_data("corrEGQ.xlsx")
corrE7X = load_corr_data("corrE7X.xlsx")

# ==================================================
# STRESS — UTILITIES (UNA SOLA VOLTA)
# ==================================================
@st.cache_data
def load_stress_list(path="StressUtilizzati.xlsx"):
    df = pd.read_excel(path, usecols=[0])
    return (
        df.iloc[:, 0]
        .dropna()
        .astype(str)
        .str.strip()
        .sort_values(key=lambda x: x.str.len(), ascending=False)
        .tolist()
    )


def split_sheet_name(sheet_name, stress_list):
    for stress in stress_list:
        token = f"_{stress}"
        if sheet_name.endswith(token):
            return sheet_name.replace(token, ""), stress
    return sheet_name, sheet_name


@st.cache_data
def load_stress_data(path, stress_list):
    xls = pd.ExcelFile(path)
    records = []

    for sheet in xls.sheet_names:
        portfolio, scenario = split_sheet_name(sheet, stress_list)
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


stress_list = load_stress_list()

# ==================================================
# TAB 1 — CORRELATION
# ==================================================
with tab_corr:
    if chart_type == "EGQ vs Index and Cash":
        df = corrEGQ.copy()
        chart_title = "EGQ vs Index and Cash"
    else:
        df = corrE7X.copy()
        chart_title = "E7X vs Funds"

    st.sidebar.subheader("Date range (Correlation)")
    start_date, end_date = st.sidebar.date_input(
        "Select start and end date",
        value=(df.index.min().date(), df.index.max().date())
    )

    df = df.loc[pd.to_datetime(start_date):pd.to_datetime(end_date)]

    st.sidebar.subheader("Series (Correlation)")
    selected_series = st.sidebar.multiselect(
        "Select series",
        df.columns.tolist(),
        default=df.columns.tolist()
    )

    if not selected_series:
        st.stop()

    palette = qualitative.Plotly
    color_map = {s: palette[i % len(palette)] for i, s in enumerate(selected_series)}

    st.title(chart_title)
    st.subheader("Correlation Time Series")

    fig = go.Figure()
    for s in selected_series:
        fig.add_trace(go.Scatter(
            x=df.index,
            y=df[s] * 100,
            name=s,
            line=dict(color=color_map[s])
        ))

    fig.update_layout(
        template="plotly_white",
        yaxis_title="Correlation (%)",
        hovermode="x unified",
        height=600
    )

    st.plotly_chart(fig, use_container_width=True)

# ==================================================
# TAB 2 — STRESS TEST
# ==================================================
with tab_stress:
    if chart_type == "EGQ vs Index and Cash":
        stress_path = "stress_test_totEGQ.xlsx"
        stress_title = "EGQ vs Index and Cash"
    else:
        stress_path = "stress_test_totE7X.xlsx"
        stress_title = "E7X vs Funds"

    stress_data = load_stress_data(stress_path, stress_list)

    st.title(stress_title)

    st.sidebar.subheader("Date (Stress Test)")
    dates = sorted(stress_data["Date"].unique())
    selected_date = st.sidebar.selectbox("Select date", dates)

    df_f = stress_data[stress_data["Date"] == selected_date]

    st.sidebar.subheader("Series (Stress Test)")
    portfolios = sorted(df_f["Portfolio"].unique())
    selected_portfolios = st.sidebar.multiselect(
        "Select series", portfolios, default=portfolios
    )

    df_f = df_f[df_f["Portfolio"].isin(selected_portfolios)]

    st.sidebar.subheader("Scenarios (Stress Test)")
    scenarios = sorted(df_f["ScenarioName"].unique())
    selected_scenarios = st.sidebar.multiselect(
        "Select stress scenarios", scenarios, default=scenarios
    )

    df_f = df_f[df_f["ScenarioName"].isin(selected_scenarios)]

    # -----------------------------
    # Grouped bar
    # -----------------------------
    fig_bar = go.Figure()
    for i, p in enumerate(selected_portfolios):
        d = df_f[df_f["Portfolio"] == p]
        fig_bar.add_trace(go.Bar(
            x=d["ScenarioName"],
            y=d["StressPnL"],
            name=p
        ))

    fig_bar.update_layout(
        barmode="group",
        template="plotly_white",
        yaxis_title="Stress PnL (bps)",
        height=600
    )

    st.plotly_chart(fig_bar, use_container_width=True)

    # -----------------------------
    # Bucket analysis (IDENTICA)
    # -----------------------------
    st.markdown("---")
    st.subheader("Comparison Analysis")

    selected_portfolio = st.selectbox(
        "Analysis portfolio", selected_portfolios
    )

    df_analysis = df_f[df_f["Portfolio"] == selected_portfolio]
    df_bucket = df_f[df_f["Portfolio"] != selected_portfolio]

    bucket_stats = (
        df_bucket
        .groupby("ScenarioName", as_index=False)
        .agg(
            bucket_median=("StressPnL", "median"),
            q25=("StressPnL", lambda x: x.quantile(0.25)),
            q75=("StressPnL", lambda x: x.quantile(0.75))
        )
    )

    df_plot = df_analysis.merge(bucket_stats, on="ScenarioName")

    fig = go.Figure()

    for _, r in df_plot.iterrows():
        fig.add_trace(go.Scatter(
            x=[r["q25"], r["q75"]],
            y=[r["ScenarioName"]] * 2,
            mode="lines",
            line=dict(width=14, color="rgba(255,0,0,0.25)"),
            showlegend=False
        ))

    fig.add_trace(go.Scatter(
        x=df_plot["bucket_median"],
        y=df_plot["ScenarioName"],
        mode="markers",
        name="Bucket median",
        marker=dict(color="red")
    ))

    fig.add_trace(go.Scatter(
        x=df_plot["StressPnL"],
        y=df_plot["ScenarioName"],
        mode="markers",
        name=selected_portfolio,
        marker=dict(symbol="star", size=14, color="orange")
    ))

    fig.update_layout(
        template="plotly_white",
        xaxis_title="Stress PnL (bps)",
        height=600
    )

    st.plotly_chart(fig, use_container_width=True)
