import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# --------------------------------------------------
# Config
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
corrE7X = load_corr_data("corrE7X.xlsx")

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
else:
    df = corrE7X.copy()
    chart_title = "E7X vs Funds"

# --------------------------------------------------
# Date filter (only available dates)
# --------------------------------------------------
available_dates = df.index.to_list()

start_date = st.sidebar.selectbox(
    "Start date",
    available_dates,
    index=0
)

end_date = st.sidebar.selectbox(
    "End date",
    available_dates,
    index=len(available_dates) - 1
)

df = df.loc[start_date:end_date]

# --------------------------------------------------
# Series selector
# --------------------------------------------------
available_series = df.columns.tolist()

selected_series = st.sidebar.multiselect(
    "Select series",
    available_series,
    default=available_series
)

# --------------------------------------------------
# Plot
# --------------------------------------------------
st.title(chart_title)

if not selected_series:
    st.warning("Select at least one series.")
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
        xaxis_title="Date",
        yaxis_title="Correlation",
        template="plotly_white",
        legend_title_text="Series"
    )

    st.plotly_chart(fig, use_container_width=True)
