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
# Sidebar controls (sempre presenti)
# --------------------------------------------------
st.sidebar.title("Controls")

chart_type = st.sidebar.selectbox(
    "Select chart",
    ["EGQ vs Index and Cash", "E7X vs Funds"]
)

# --------------------------------------------------
# Correlation data loader
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
# Stress name utilities
# --------------------------------------------------
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
        suffix = f"_{stress}"
        if sheet_name.endswith(suffix):
            portfolio = sheet_name[:-len(suffix)]
            return portfolio, stress

    st.warning(f"⚠️ Stress non riconosciuto nel foglio: {sheet_name}")
    return sheet_name, "UNKNOWN"


@st.cache_data
def load_stress_data(path, stress_list):
    xls = pd.ExcelFile(path)
    records = []

    for sheet_name in xls.sheet_names:
        portfolio, scenario_name = split_sheet_name(sheet_name, stress_list)

        df = pd.read_excel(xls, sheet_name=sheet_name)
        df = df.rename(columns={
            df.columns[0]: "Date",
            df.columns[2]: "Scenario",
            df.columns[4]: "StressPnL"
        })

        df["Date"] = pd.to_datetime(df["Date"])
        df["Portfolio"] = portfolio
        df["ScenarioName"] = scenario_name

        records.append(
            df[["Date", "Scenario", "StressPnL", "Portfolio", "ScenarioName"]]
        )

    return pd.concat(records, ignore_index=True)


stress_list = load_stress_list()

# --------------------------------------------------
# TAB 1 — CORRELATION
# --------------------------------------------------
with tab_corr:
    st.session_state.current_tab = "Correlation"

    if chart_type == "EGQ vs Index and Cash":
        df = corrEGQ.copy()
        chart_title = "EGQ vs Index and Cash"
    else:
        df = corrE7X.copy()
        chart_title = "E7X vs Funds"

    st.sidebar.subheader("Date range (Correlation)")
    start_date, end_date = st.sidebar.date_input(
        "Select start and end date",
        value=(df.index.min().date(), df.index.max().date()),
        min_value=df.index.min().date(),
        max_value=df.index.max().date()
    )

    df = df.loc[pd.to_datetime(start_date):pd.to_datetime(end_date)]

    st.sidebar.subheader("Series (Correlation)")
    selected_series = st.sidebar.multiselect(
        "Select series",
        options=df.columns.tolist(),
        default=df.columns.tolist()
    )

    if not selected_series:
        st.stop()

    palette = qualitative.Plotly
    color_map = {s: palette[i % len(palette)] for i, s in enumerate(selected_series)}

    st.title(chart_title)
    st.subheader("Correlation Time Series")

    fig_ts = go.Figure()
    for col in selected_series:
        fig_ts.add_trace(
            go.Scatter(
                x=df.index,
                y=df[col] * 100,
                name=col,
                mode="lines",
                line=dict(color=color_map[col]),
                hovertemplate="%{y:.2f}%<extra></extra>"
            )
        )

    fig_ts.update_layout(
        height=600,
        hovermode="x unified",
        template="plotly_white",
        yaxis=dict(ticksuffix="%")
    )

    st.plotly_chart(fig_ts, use_container_width=True)

    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        (df[selected_series] * 100).to_excel(writer)

    st.download_button(
        "📥 Download time series data as Excel",
        output.getvalue(),
        "time_series_data.xlsx"
    )

    st.subheader("Correlation Radar")

    snapshot = df[selected_series].iloc[-1]
    mean_corr = df[selected_series].mean()

    fig_radar = go.Figure()
    fig_radar.add_trace(go.Scatterpolar(
        r=snapshot.values * 100,
        theta=snapshot.index,
        name="End date"
    ))
    fig_radar.add_trace(go.Scatterpolar(
        r=mean_corr.values * 100,
        theta=mean_corr.index,
        name="Period mean",
        line=dict(dash="dot")
    ))

    fig_radar.update_layout(
        polar=dict(radialaxis=dict(range=[-100, 100], ticksuffix="%")),
        height=650
    )

    st.plotly_chart(fig_radar, use_container_width=True)

    st.subheader("Summary statistics")

    stats_df = pd.DataFrame(index=selected_series)
    stats_df["Mean (%)"] = df[selected_series].mean() * 100
    stats_df["Min (%)"] = df[selected_series].min() * 100
    stats_df["Max (%)"] = df[selected_series].max() * 100

    st.dataframe(stats_df.style.format("{:.2f}%"), use_container_width=True)

    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        stats_df.to_excel(writer)

    st.download_button(
        "📥 Download summary statistics as Excel",
        output.getvalue(),
        "summary_statistics.xlsx"
    )

# --------------------------------------------------
# TAB 2 — STRESS TEST
# --------------------------------------------------
if chart_type == "EGQ vs Index and Cash":
    stress_path = "stress_test_totEGQ.xlsx"
    stress_title = "EGQ vs Index and Cash"
else:
    stress_path = "stress_test_totE7X.xlsx"
    stress_title = "E7X vs Funds"

stress_data = load_stress_data(stress_path, stress_list)

with tab_stress:
    st.session_state.current_tab = "StressTest"
    st.title(stress_title)

    st.sidebar.subheader("Date (Stress Test)")
    dates = sorted(stress_data["Date"].unique())
    selected_date = st.sidebar.selectbox("Select date", dates)

    df_filtered = stress_data[stress_data["Date"] == selected_date]

    st.sidebar.subheader("Series (Stress Test)")
    portfolios = df_filtered["Portfolio"].unique().tolist()
    selected_portfolios = st.sidebar.multiselect(
        "Select series",
        portfolios,
        default=portfolios
    )

    df_filtered = df_filtered[df_filtered["Portfolio"].isin(selected_portfolios)]

    st.sidebar.subheader("Scenarios (Stress Test)")
    scenarios = df_filtered["ScenarioName"].unique().tolist()
    selected_scenarios = st.sidebar.multiselect(
        "Select stress scenarios",
        scenarios,
        default=scenarios
    )

    df_filtered = df_filtered[df_filtered["ScenarioName"].isin(selected_scenarios)]

    st.subheader("Stress Test PnL")

    fig_bar = go.Figure()
    for i, p in enumerate(selected_portfolios):
        tmp = df_filtered[df_filtered["Portfolio"] == p]
        fig_bar.add_trace(go.Bar(
            x=tmp["ScenarioName"],
            y=tmp["StressPnL"],
            name=p
        ))

    fig_bar.update_layout(barmode="group", height=600)
    st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown(
        """
        <div style="display:flex;align-items:center;">
        <sub>Note: shaded areas represent the 25–75 percentile dispersion of the Bucket.</sub>
        </div>
        """,
        unsafe_allow_html=True
    )
