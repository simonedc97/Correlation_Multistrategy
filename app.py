import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import networkx as nx
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
# Load data
# --------------------------------------------------
@st.cache_data
def load_corr_data(path):
    df = pd.read_excel(path, sheet_name="Correlation Clean")
    df.iloc[:, 0] = pd.to_datetime(df.iloc[:, 0])
    df = df.set_index(df.columns[0]).sort_index()
    return df

corrEGQ = load_corr_data("corrEGQ.xlsx")
corrE7X = load_corr_data("corrE7X.xlsx")

# ==================================================
# TAB 1 — CORRELATION
# ==================================================
with tab_corr:

    # --------------------------------------------------
    # Sidebar controls
    # --------------------------------------------------
    st.sidebar.title("Controls")

    chart_type = st.sidebar.selectbox(
        "Select chart",
        ["EGQ vs Index and Cash", "E7X vs Funds"]
    )

    if chart_type == "EGQ vs Index and Cash":
        df = corrEGQ.copy()
        chart_title = "EGQ vs Index and Cash"
        reference_asset = "EGQ"
    else:
        df = corrE7X.copy()
        chart_title = "E7X vs Funds"
        reference_asset = "E7X"

    # --------------------------------------------------
    # Date picker
    # --------------------------------------------------
    st.sidebar.subheader("Date range")

    start_date, end_date = st.sidebar.date_input(
        "Select start and end date",
        value=(df.index.min().date(), df.index.max().date()),
        min_value=df.index.min().date(),
        max_value=df.index.max().date()
    )

    df = df.loc[pd.to_datetime(start_date):pd.to_datetime(end_date)]

    # --------------------------------------------------
    # Series selector
    # --------------------------------------------------
    st.sidebar.subheader("Series")

    selected_series = st.sidebar.multiselect(
        "Select series",
        options=df.columns.tolist(),
        default=df.columns.tolist()
    )

    if not selected_series:
        st.warning("Please select at least one series.")
        st.stop()

    # --------------------------------------------------
    # Color map
    # --------------------------------------------------
    palette = qualitative.Plotly
    color_map = {
        s: palette[i % len(palette)]
        for i, s in enumerate(selected_series)
    }

    # --------------------------------------------------
    # Title
    # --------------------------------------------------
    st.title(chart_title)

    # --------------------------------------------------
    # Time series plot
    # --------------------------------------------------
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

    # --------------------------------------------------
    # Radar chart
    # --------------------------------------------------
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
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[-100, 100],
                ticksuffix="%"
            )
        ),
        template="plotly_white",
        height=650
    )

    st.plotly_chart(fig_radar, use_container_width=True)

    # --------------------------------------------------
    # Summary statistics
    # --------------------------------------------------
    st.subheader("Summary statistics")

    stats_df = pd.DataFrame(index=selected_series)

    stats_df["Mean (%)"] = df[selected_series].mean() * 100

    stats_df["Min (%)"] = df[selected_series].min() * 100
    stats_df["Min Date"] = [
        df[col][df[col] == df[col].min()].index.max()
        for col in selected_series
    ]

    stats_df["Max (%)"] = df[selected_series].max() * 100
    stats_df["Max Date"] = [
        df[col][df[col] == df[col].max()].index.max()
        for col in selected_series
    ]

    stats_df["Min Date"] = pd.to_datetime(stats_df["Min Date"]).dt.strftime("%d/%m/%Y")
    stats_df["Max Date"] = pd.to_datetime(stats_df["Max Date"]).dt.strftime("%d/%m/%Y")

    # --------------------------------------------------
    # Download button (Excel with 2 sheets)
    # --------------------------------------------------
    file_start = pd.to_datetime(start_date).strftime("%Y%m%d")
    file_end = pd.to_datetime(end_date).strftime("%Y%m%d")
    file_name = f"summary_statistics_{file_start}_{file_end}.xlsx"

    output = BytesIO()

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:

        # Sheet 1 - Correlation
        (
            stats_df
            .reset_index()
            .rename(columns={"index": "Asset"})
            .to_excel(writer, sheet_name="Correlation", index=False)
        )

        # Sheet 2 - Stress Test (vuoto)
        pd.DataFrame().to_excel(writer, sheet_name="Stress Test", index=False)

    output.seek(0)

    st.download_button(
        label="Download summary table (Excel)",
        data=output,
        file_name=file_name,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # --------------------------------------------------
    # Table display
    # --------------------------------------------------
    st.dataframe(
        stats_df.style.format({
            "Mean (%)": "{:.2f}%",
            "Min (%)": "{:.2f}%",
            "Max (%)": "{:.2f}%"
        }),
        use_container_width=True
    )

# ==================================================
# TAB 2 — STRESS TEST
# ==================================================
with tab_corr:
    st.title(chart_title)
