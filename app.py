import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# --------------------------------------------------
# Page config
# --------------------------------------------------
st.set_page_config(layout="wide")

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
# Sidebar controls
# --------------------------------------------------
st.sidebar.title("Controls")

# 🔁 SCELTA GRAFICO COME PRIMA
chart_type = st.sidebar.selectbox(
    "Select chart",
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
st.sidebar.subheader("Date range")

min_date = df.index.min().date()
max_date = df.index.max().date()

start_date, end_date = st.sidebar.date_input(
    "Select start and end date",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

df = df.loc[pd.to_datetime(start_date):pd.to_datetime(end_date)]

st.sidebar.divider()

# --------------------------------------------------
# Serie selector (nome GENERICO)
# --------------------------------------------------
st.sidebar.subheader("Series")

available_series = df.columns.tolist()

selected_series = st.sidebar.multiselect(
    "Select series to display",
    options=available_series,
    default=available_series
)

# --------------------------------------------------
# Main
# --------------------------------------------------
st.title(chart_title)

# --------------------------------------------------
# Plot (COME PRIMA)
# --------------------------------------------------
if not selected_series:
    st.warning("Please select at least one series.")
else:
    fig = go.Figure()

    for col in selected_series:
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df[col],
                mode="lines",
                name=col
            )
        )

    fig.update_layout(
        height=600,
        hovermode="x unified",
        template="plotly_white",
        xaxis_title="Date",
        yaxis_title="Correlation",
        legend_title_text="Series"
    )

    st.plotly_chart(fig, use_container_width=True)
