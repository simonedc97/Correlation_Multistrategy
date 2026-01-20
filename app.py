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

# ==================================================
# TAB 2 — STRESS TEST
# ==================================================
with tab_stress:
    st.session_state.current_tab = "StressTest"
    st.title("Stress Test Analysis")

    # -----------------------------
    # Date selector solo qui
    # -----------------------------
    st.sidebar.subheader("Date (Stress Test)")
    all_dates = stress_data["Date"].sort_values().unique()
    # Formatta le date in formato YYYY/MM/DD
    date_options = [d.strftime("%Y/%m/%d") for d in all_dates]
    selected_date_str = st.sidebar.selectbox("Select date", date_options)
    # Converti la data selezionata in datetime per filtrare il DataFrame
    selected_date = pd.to_datetime(selected_date_str, format="%Y/%m/%d")

    # Filtra per data selezionata
    df_filtered = stress_data[stress_data["Date"] == selected_date]

    if df_filtered.empty:
        st.warning("No data available for the selected date.")
    else:
        # -----------------------------
        # Plot grouped bar chart per portafoglio
        # -----------------------------
        fig_bar = go.Figure()
        portfolios = df_filtered["Portfolio"].unique()
        palette = qualitative.Plotly

        for i, portfolio in enumerate(portfolios):
            df_port = df_filtered[df_filtered["Portfolio"] == portfolio]
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
            title=f"Stress Test PnL on {selected_date.strftime('%Y/%m/%d')}",
            xaxis_title="Scenario",
            yaxis_title="Stress PnL (bps)",
            template="plotly_white",
            height=600
        )

        st.plotly_chart(fig_bar, use_container_width=True)

        # -----------------------------
        # Portfolio vs Peer Stats (box-like)
        # -----------------------------
        st.subheader("Portfolio vs Peer Median and Quantiles")

        # Sidebar per scegliere il portafoglio da confrontare
        selected_portfolio = st.sidebar.selectbox(
            "Select portfolio for peer comparison",
            portfolios,
            index=0
        )

        # Filtra i dati del portafoglio selezionato e dei peer
        df_port = df_filtered[df_filtered["Portfolio"] == selected_portfolio]
        df_peers = df_filtered[df_filtered["Portfolio"] != selected_portfolio]

        # Calcola median, mean e quantili dei peer
        peer_stats = df_peers.groupby("ScenarioName")["StressPnL"].agg(
            peer_mean="mean",
            peer_q15=lambda x: x.quantile(0.15),
            peer_q75=lambda x: x.quantile(0.75)
        ).reindex(df_port["ScenarioName"])

        # Scatter plot
        fig_scatter = go.Figure()

        # Banda quantili (riempita)
        fig_scatter.add_trace(
            go.Scatter(
                x=peer_stats["peer_q75"],
                y=peer_stats.index,
                mode='lines',
                line=dict(width=0),
                showlegend=False
            )
        )
        fig_scatter.add_trace(
            go.Scatter(
                x=peer_stats["peer_q15"],
                y=peer_stats.index,
                mode='lines',
                fill='tonextx',
                fillcolor='rgba(173,216,230,0.3)',  # banda azzurra chiara
                line=dict(width=0),
                name='Peer 15-75 Quantile'
            )
        )

        # Puntino media peer
        fig_scatter.add_trace(
            go.Scatter(
                x=peer_stats["peer_mean"],
                y=peer_stats.index,
                mode='markers',
                marker=dict(color='red', size=10),
                name='Peer Mean'
            )
        )

        # Puntino portafoglio selezionato
        fig_scatter.add_trace(
            go.Scatter(
                x=df_port["StressPnL"],
                y=df_port["ScenarioName"],
                mode='markers',
                marker=dict(color='blue', size=12),
                name=selected_portfolio
            )
        )

        fig_scatter.update_layout(
            title=f"{selected_portfolio} vs Peer Stats on {selected_date.strftime('%Y/%m/%d')}",
            xaxis_title="Stress PnL (bps)",
            yaxis_title="Scenario",
            template="plotly_white",
            height=600,
            hovermode="y"
        )

        st.plotly_chart(fig_scatter, use_container_width=True)
