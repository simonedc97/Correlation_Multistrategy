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

# Chart selector sempre presente
chart_type = st.sidebar.selectbox(
    "Select chart",
    ["EGQ vs Index and Cash", "E7X vs Funds"]
)

# --------------------------------------------------
# Funzione per caricamento dati Correlation
# --------------------------------------------------
@st.cache_data
def load_corr_data(path):
    df = pd.read_excel(path, sheet_name="Correlation Clean")
    df.iloc[:, 0] = pd.to_datetime(df.iloc[:, 0])
    df = df.set_index(df.columns[0]).sort_index()
    return df

# Caricamento dati Correlation
corrEGQ = load_corr_data("corrEGQ.xlsx")
corrE7X = load_corr_data("corrE7X.xlsx")

# --------------------------------------------------
# Funzione per caricamento dati Stress Test
# --------------------------------------------------
@st.cache_data
def load_stress_data(path):
    xls = pd.ExcelFile(path)
    records = []
    for sheet_name in xls.sheet_names:
        if "_" in sheet_name:
            portfolio, scenario_name = sheet_name.split("_", 1)
        else:
            portfolio, scenario_name = sheet_name, sheet_name
        df = pd.read_excel(xls, sheet_name=sheet_name)
        df = df.rename(columns={
            df.columns[0]: "Date",
            df.columns[2]: "Scenario",
            df.columns[4]: "StressPnL"
        })
        df["Date"] = pd.to_datetime(df["Date"])
        df["Portfolio"] = portfolio
        df["ScenarioName"] = scenario_name
        records.append(df[["Date", "Scenario", "StressPnL", "Portfolio", "ScenarioName"]])
    return pd.concat(records, ignore_index=True)

stress_data = load_stress_data("stress_test_totE7X.xlsx")

# ==================================================
# TAB 1 — CORRELATION
# ==================================================
with tab_corr:
    st.session_state.current_tab = "Correlation"

    # Selezione dataframe in base al chart_type
    if chart_type == "EGQ vs Index and Cash":
        df = corrEGQ.copy()
        chart_title = "EGQ vs Index and Cash"
        reference_asset = "EGQ"
    else:
        df = corrE7X.copy()
        chart_title = "E7X vs Funds"
        reference_asset = "E7X"

    # -----------------------------
    # Date range picker solo qui
    # -----------------------------
    st.sidebar.subheader("Date range (Correlation)")
    start_date, end_date = st.sidebar.date_input(
        "Select start and end date",
        value=(df.index.min().date(), df.index.max().date()),
        min_value=df.index.min().date(),
        max_value=df.index.max().date()
    )
    df = df.loc[pd.to_datetime(start_date):pd.to_datetime(end_date)]

    # -----------------------------
    # Series selector
    # -----------------------------
    st.sidebar.subheader("Series (Correlation)")
    selected_series = st.sidebar.multiselect(
        "Select series",
        options=df.columns.tolist(),
        default=df.columns.tolist()
    )
    if not selected_series:
        st.warning("Please select at least one series.")
        st.stop()

    # -----------------------------
    # Color map
    # -----------------------------
    palette = qualitative.Plotly
    color_map = {s: palette[i % len(palette)] for i, s in enumerate(selected_series)}

    # -----------------------------
    # Title
    # -----------------------------
    st.title(chart_title)

    # -----------------------------
    # Time series plot
    # -----------------------------
    st.subheader("Correlation Time Series")
    fig_ts = go.Figure()
    for col in selected_series:
        fig_ts.add_trace(
            go.Scatter(
                x=df.index,
                y=df[col] * 100,
                mode="lines",
                name=col,
                line=dict(color=color_map[col]),
                hovertemplate="%{y:.2f}%<extra></extra>"
            )
        )
    fig_ts.update_layout(
        height=600,
        hovermode="x unified",
        template="plotly_white",
        yaxis=dict(ticksuffix="%"),
        xaxis_title="Date",
        yaxis_title="Correlation"
    )
    st.plotly_chart(fig_ts, use_container_width=True)
    # Dati sottostanti al grafico (in percentuale, coerente con il grafico)
    df_download = df[selected_series] * 100
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_download.to_excel(writer, sheet_name="Time Series Data")
    
    st.download_button(
        label="📥 Download time series data as Excel",
        data=output.getvalue(),
        file_name="time_series_data.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="download_time_series"
    )
    # -----------------------------
    # Radar chart
    # -----------------------------
    st.subheader("Correlation Radar")
    snapshot_date = df.index.max()
    snapshot = df.loc[snapshot_date, selected_series]
    mean_corr = df[selected_series].mean()

    fig_radar = go.Figure()
    fig_radar.add_trace(
        go.Scatterpolar(
            r=snapshot.values * 100,
            theta=snapshot.index,
            name=f"End date ({snapshot_date.date()})",
            line=dict(width=3)
        )
    )
    fig_radar.add_trace(
        go.Scatterpolar(
            r=mean_corr.values * 100,
            theta=mean_corr.index,
            name="Period mean",
            line=dict(dash="dot")
        )
    )
    fig_radar.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[-100, 100], ticksuffix="%")),
        template="plotly_white",
        height=650
    )
    st.plotly_chart(fig_radar, use_container_width=True)

    # -----------------------------
    # Summary statistics
    # -----------------------------
    st.subheader("Summary statistics")
    stats_df = pd.DataFrame(index=selected_series)
    stats_df["Mean (%)"] = df[selected_series].mean() * 100
    stats_df["Min (%)"] = df[selected_series].min() * 100
    stats_df["Min Date"] = [df[col][df[col] == df[col].min()].index.max() for col in selected_series]
    stats_df["Max (%)"] = df[selected_series].max() * 100
    stats_df["Max Date"] = [df[col][df[col] == df[col].max()].index.max() for col in selected_series]
    stats_df["Min Date"] = pd.to_datetime(stats_df["Min Date"]).dt.strftime("%d/%m/%Y")
    stats_df["Max Date"] = pd.to_datetime(stats_df["Max Date"]).dt.strftime("%d/%m/%Y")
    st.dataframe(stats_df.style.format({"Mean (%)": "{:.2f}%", "Min (%)": "{:.2f}%", "Max (%)": "{:.2f}%"}), use_container_width=True)

    # -----------------------------
    # Bottone di download Excel
    # -----------------------------
    from io import BytesIO
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        stats_df.to_excel(writer, sheet_name="Summary Stats")
    
    st.download_button(
        label="📥 Download summary statistics as Excel",
        data=output.getvalue(),
        file_name="summary_statistics.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="download_summary_stats"
    )
# ==================================================
# TAB 2 — STRESS TEST
# ==================================================
# --------------------------------------------------
# Funzione per caricamento dati Stress Test
# --------------------------------------------------
@st.cache_data
def load_stress_data(path):
    xls = pd.ExcelFile(path)
    records = []

    for sheet_name in xls.sheet_names:
        if "_" in sheet_name:
            portfolio, scenario_name = sheet_name.split("_", 1)
        else:
            portfolio, scenario_name = sheet_name, sheet_name

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


# --------------------------------------------------
# Selezione file Stress Test in base al chart_type
# --------------------------------------------------
if chart_type == "EGQ vs Index and Cash":
    stress_path = "stress_test_totEGQ.xlsx"
    stress_title = "EGQ vs Index and Cash"
else:
    stress_path = "stress_test_totE7X.xlsx"
    stress_title = "E7X vs Funds"

stress_data = load_stress_data(stress_path)


# ==================================================
# TAB — STRESS TEST
# ==================================================
# --------------------------------------------------
# Funzione per caricamento dati Stress Test
# --------------------------------------------------
@st.cache_data
def load_stress_data(path):
    xls = pd.ExcelFile(path)
    records = []

    for sheet_name in xls.sheet_names:
        if "_" in sheet_name:
            portfolio, scenario_name = sheet_name.split("_", 1)
        else:
            portfolio, scenario_name = sheet_name, sheet_name

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


# --------------------------------------------------
# Selezione file Stress Test in base al chart_type
# --------------------------------------------------
if chart_type == "EGQ vs Index and Cash":
    stress_path = "stress_test_totEGQ.xlsx"
    stress_title = "EGQ vs Index and Cash"
else:
    stress_path = "stress_test_totE7X.xlsx"
    stress_title = "E7X vs Funds"

stress_data = load_stress_data(stress_path)


# ==================================================
# STRESS TEST — DATA LOADING
# ==================================================
@st.cache_data
def load_stress_data(path):
    xls = pd.ExcelFile(path)
    records = []

    for sheet_name in xls.sheet_names:
        if "_" in sheet_name:
            portfolio, scenario_name = sheet_name.split("_", 1)
        else:
            portfolio, scenario_name = sheet_name, sheet_name

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


# --------------------------------------------------
# Select Stress Test file based on chart_type
# --------------------------------------------------
if chart_type == "EGQ vs Index and Cash":
    stress_path = "stress_test_totEGQ.xlsx"
    stress_title = "EGQ vs Index and Cash"
else:
    stress_path = "stress_test_totE7X.xlsx"
    stress_title = "E7X vs Funds"

stress_data = load_stress_data(stress_path)


# ==================================================
# STRESS TEST — DATA LOADING
# ==================================================
@st.cache_data
def load_stress_data(path):
    xls = pd.ExcelFile(path)
    records = []

    for sheet_name in xls.sheet_names:
        if "_" in sheet_name:
            portfolio, scenario_name = sheet_name.split("_", 1)
        else:
            portfolio, scenario_name = sheet_name, sheet_name

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


# --------------------------------------------------
# Select Stress Test file based on chart_type
# --------------------------------------------------
if chart_type == "EGQ vs Index and Cash":
    stress_path = "stress_test_totEGQ.xlsx"
    stress_title = "EGQ vs Index and Cash"
else:
    stress_path = "stress_test_totE7X.xlsx"
    stress_title = "E7X vs Funds"

stress_data = load_stress_data(stress_path)


# ==================================================
# TAB — STRESS TEST
# ==================================================
with tab_stress:
    st.session_state.current_tab = "StressTest"
    st.title(stress_title)

    # -----------------------------
    # Date selector
    # -----------------------------
    st.sidebar.subheader("Date (Stress Test)")

    all_dates = (
        stress_data["Date"]
        .dropna()
        .sort_values()
        .unique()
    )

    date_options = [d.strftime("%Y/%m/%d") for d in all_dates]

    selected_date_str = st.sidebar.selectbox(
        "Select date",
        date_options
    )

    selected_date = pd.to_datetime(
        selected_date_str,
        format="%Y/%m/%d"
    )

    df_filtered = stress_data[
        stress_data["Date"] == selected_date
    ]

    if df_filtered.empty:
        st.warning("No data available for the selected date.")
        st.stop()

    # -----------------------------
    # Portfolio selector
    # -----------------------------
    st.sidebar.subheader("Series (Stress Test)")

    available_portfolios = (
        df_filtered["Portfolio"]
        .dropna()
        .sort_values()
        .unique()
        .tolist()
    )

    selected_portfolios = st.sidebar.multiselect(
        "Select series",
        options=available_portfolios,
        default=available_portfolios
    )

    if not selected_portfolios:
        st.warning("Please select at least one portfolio.")
        st.stop()

    df_filtered = df_filtered[
        df_filtered["Portfolio"].isin(selected_portfolios)
    ]

    # -----------------------------
    # Scenario selector
    # -----------------------------
    st.sidebar.subheader("Scenarios (Stress Test)")

    available_scenarios = (
        df_filtered["ScenarioName"]
        .dropna()
        .sort_values()
        .unique()
        .tolist()
    )

    selected_scenarios = st.sidebar.multiselect(
        "Select stress scenarios",
        options=available_scenarios,
        default=available_scenarios
    )

    if not selected_scenarios:
        st.warning("Please select at least one stress scenario.")
        st.stop()

    df_filtered = df_filtered[
        df_filtered["ScenarioName"].isin(selected_scenarios)
    ]

    # Preserve user order
    df_filtered["ScenarioName"] = pd.Categorical(
        df_filtered["ScenarioName"],
        categories=selected_scenarios,
        ordered=True
    )

    df_filtered["Portfolio"] = pd.Categorical(
        df_filtered["Portfolio"],
        categories=selected_portfolios,
        ordered=True
    )

    # -----------------------------
    # Stress Test PnL – Grouped bar
    # -----------------------------
    st.subheader("Stress Test PnL")

    fig_bar = go.Figure()
    palette = qualitative.Plotly

    for i, portfolio in enumerate(selected_portfolios):
        df_port = df_filtered[
            df_filtered["Portfolio"] == portfolio
        ]

        if df_port.empty:
            continue

        fig_bar.add_trace(
            go.Bar(
                x=df_port["ScenarioName"],
                y=df_port["StressPnL"],
                name=portfolio,
                marker_color=palette[i % len(palette)],
                text=df_port["StressPnL"],
                textposition="auto"
            )
        )

    fig_bar.update_layout(
        barmode="group",
        xaxis_title="Scenario",
        yaxis_title="Stress PnL (bps)",
        template="plotly_white",
        height=600
    )

    st.plotly_chart(fig_bar, use_container_width=True)

    df_download = df_filtered[df_filtered["Portfolio"].isin(selected_portfolios)][
        ["Portfolio", "ScenarioName", "StressPnL"]
    ]
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_download.to_excel(writer, sheet_name="Stress Test PnL", index=False)
    
    st.download_button(
        label="📥 Download Stress PnL data as Excel",
        data=output.getvalue(),
        file_name="stress_test_pnl.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="download_stress_pnl"
    )   
    # -----------------------------
    # Portfolio vs Bucket Analysis
    # -----------------------------
    st.markdown("---")
    st.subheader("Comparison Analysis")
    
    selected_portfolio = st.selectbox(
        "Analysis portfolio",
        selected_portfolios,
        index=0
    )
    
    # Dati del portfolio selezionato
    df_analysis = df_filtered[
        df_filtered["Portfolio"] == selected_portfolio
    ][["ScenarioName", "StressPnL"]]
    
    # Dati degli altri portafogli, ora considerati come Bucket
    df_bucket = df_filtered[
        df_filtered["Portfolio"] != selected_portfolio
    ][["ScenarioName", "StressPnL"]]
    
    if df_bucket.empty:
        st.warning("Not enough portfolios selected for bucket comparison.")
        st.stop()
    
    # Calcolo mediana e quantili del Bucket
    df_bucket_stats = (
        df_bucket
        .groupby("ScenarioName", as_index=False)
        .agg(
            bucket_median=("StressPnL", "median"),
            q25=("StressPnL", lambda x: x.quantile(0.25)),
            q75=("StressPnL", lambda x: x.quantile(0.75))
        )
    )
    
    # Merge dei dati per il plot
    df_plot = df_analysis.merge(
        df_bucket_stats,
        on="ScenarioName",
        how="inner"
    )
    
    fig = go.Figure()
    
    # Q25–Q75 range (barra ombreggiata)
    for _, r in df_plot.iterrows():
        fig.add_trace(
            go.Scatter(
                x=[r["q25"], r["q75"]],
                y=[r["ScenarioName"], r["ScenarioName"]],
                mode="lines",
                line=dict(width=14, color="rgba(255,0,0,0.25)"),
                showlegend=False,  # non appare nella legenda
                hoverinfo="skip"
            )
        )
    
    # Bucket median
    fig.add_trace(
        go.Scatter(
            x=df_plot["bucket_median"],
            y=df_plot["ScenarioName"],
            mode="markers",
            marker=dict(size=9, color="red"),
            name="Bucket median"
        )
    )
    
    # Selected portfolio
    fig.add_trace(
        go.Scatter(
            x=df_plot["StressPnL"],
            y=df_plot["ScenarioName"],
            mode="markers",
            marker=dict(size=14, symbol="star", color="orange"),
            name=selected_portfolio
        )
    )
    
    fig.update_layout(
        xaxis_title="Stress PnL (bps)",
        yaxis_title="Scenario",
        template="plotly_white",
        height=600,
        hovermode="y"
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    st.markdown(
        """
        <div style="display: flex; align-items: center;">
            <sub style="margin-right: 4px;">Note: the shaded areas</sub>
            <div style="width: 20px; height: 14px; background-color: rgba(255,0,0,0.25); margin: 0 4px 0 0; border: 1px solid rgba(0,0,0,0.1);"></div>
            <sub>represent the dispersion between the 25th and 75th percentile of the Bucket.</sub>
        </div>
        """,
        unsafe_allow_html=True
    )



    # -----------------------------
    # Bottone di download Excel dei dati del grafico
    # -----------------------------
    
    # Dati da scaricare
    df_download = df_plot.rename(columns={
        "bucket_median": "Bucket Portfolio Median",
        "q25": "25% Quantile",
        "q75": "75% Quantile",
        "StressPnL": selected_portfolio
    })
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_download.to_excel(writer, sheet_name="Portfolio vs Bucket", index=False)
    
    st.download_button(
        label=f"📥 Download {selected_portfolio} vs Bucket data as Excel",
        data=output.getvalue(),
        file_name=f"{selected_portfolio}_vs_bucket.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key=f"download_{selected_portfolio}_vs_bucket"
    )

