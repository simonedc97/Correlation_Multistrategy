import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# --------------------------------------------------
# Page config
# --------------------------------------------------
st.set_page_config(
    page_title="Correlation Dashboard",
    layout="wide"
)

# --------------------------------------------------
# Load data
# --------------------------------------------------
@st.cache_data
def load_corr_data(path):
    df = pd.read_excel(path, sheet_name="Correlation Clean")
    df.iloc[:, 0] = pd.to_datetime(df.iloc[:, 0])
    df = df.set_index(df.columns[0])
    df = df.sort_index()
    return df


corrEGQ = load_corr_data("corrEGQ.xlsx")
corrE7U = load_corr_data("corrE7X.xlsx")

# --------------------------------------------------
# Sidebar – controls
# --------------------------------------------------
st.sidebar.title("📊 Chart Controls")

chart_type = st.sidebar.radio(
    "Dataset",
    ["EGQ vs Index and Cash", "E7X vs Funds"]
)

if chart_type == "EGQ vs Index and Cash":
    df = corrEGQ.copy()
    chart_title = "EGQ vs Index and Cash"
else:
    df = corrE7U.copy()
    chart_title = "E7X vs Funds"

st.sidebar.divider()

# --------------------------------------------------
# Date picker (calendar)
# --------------------------------------------------
st.sidebar.subheader("📅 Date Range")

min_date = df.index.min().date()
max_date = df.index.max().date()

start_date, end_date = st.sidebar.date_input(
    "Select date range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

df = df.loc[pd.to_datetime(start_date):pd.to_datetime(end_date)]

st.sidebar.divider()

# --------------------------------------------------
# Series selector
# --------------------------------------------------
st.sidebar.subheader("📈 Indices")

available_series = df.columns.tolist()

selected_series = st.sidebar.multiselect(
    "Select indices to display",
    options=available_series,
    default=available_series
)

# --------------------------------------------------
# Main title
# --------------------------------------------------
st.title(chart_title)
st.caption("Interactive correlation analysis")

# --------------------------------------------------
# Plot
# --------------------------------------------------
if not selected_series:
    st.warning("Please select at least one index.")
else:
    fig = go.Figure()

    for col in selected_series:
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df[col],
                mode="lines",
                name=col,
                line=dict(width=2)
            )
        )

    fig.update_layout(
        height=650,
        template="plotly_white",
        hovermode="x unified",
        xaxis=dict(
            title="Date",
            showgrid=True,
            rangeslider=dict(visible=True)
        ),
        yaxis=dict(
            title="Correlation",
            zeroline=True,
            zerolinewidth=1,
            zerolinecolor="black"
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )

    st.plotly_chart(fig, use_container_width=True)
