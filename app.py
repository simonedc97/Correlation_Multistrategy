import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import networkx as nx
from plotly.colors import qualitative

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

st.sidebar.divider()

# --------------------------------------------------
# Date picker
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
# Series selector
# --------------------------------------------------
st.sidebar.subheader("Series")

with st.sidebar.expander("Select / deselect series", expanded=False):
    available_series = df.columns.tolist()
    selected_series = st.multiselect(
        "",
        options=available_series,
        default=available_series
    )

# --------------------------------------------------
# Main
# --------------------------------------------------
st.title(chart_title)

if not selected_series:
    st.warning("Please select at least one series.")
    st.stop()

# --------------------------------------------------
# COLOR MAP (CHIAVE DI TUTTO)
# --------------------------------------------------
palette = qualitative.Plotly
color_map = {
    serie: palette[i % len(palette)]
    for i, serie in enumerate(selected_series)
}

# --------------------------------------------------
# Time series plot
# --------------------------------------------------
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
    xaxis_title="Date",
    yaxis_title="Correlation",
    yaxis=dict(ticksuffix="%")
)

st.plotly_chart(fig_ts, use_container_width=True)

# --------------------------------------------------
# Radar chart
# --------------------------------------------------
st.subheader("🕸️ Correlation snapshot")

snapshot_date = df.index.max()
snapshot = df.loc[snapshot_date, selected_series] * 100
mean_corr = df[selected_series].mean() * 100

fig_radar = go.Figure()

for serie in selected_series:
    fig_radar.add_trace(
        go.Scatterpolar(
            r=[snapshot[serie], mean_corr[serie]],
            theta=[serie, serie],
            mode="lines+markers",
            name=serie,
            line=dict(color=color_map[serie])
        )
    )

fig_radar.update_layout(
    polar=dict(
        radialaxis=dict(range=[-100, 100], ticksuffix="%")
    ),
    template="plotly_white",
    height=650
)

st.plotly_chart(fig_radar, use_container_width=True)

# --------------------------------------------------
# MST – INTERACTIVE (COLORI COERENTI)
# --------------------------------------------------
st.subheader("🌳 Minimum Spanning Tree (end date)")

corrl = df[selected_series].corr()
distances = np.sqrt(2 * (1 - corrl))

G = nx.Graph()
for i in corrl.index:
    for j in corrl.columns:
        if i < j:
            G.add_edge(i, j, weight=distances.loc[i, j])

mst = nx.minimum_spanning_tree(G, weight="weight")
pos = nx.spring_layout(mst, seed=42)

# Edges
edge_x, edge_y = [], []
for u, v in mst.edges():
    x0, y0 = pos[u]
    x1, y1 = pos[v]
    edge_x += [x0, x1, None]
    edge_y += [y0, y1, None]

edge_trace = go.Scatter(
    x=edge_x,
    y=edge_y,
    mode="lines",
    line=dict(color="gray", width=1),
    hoverinfo="none"
)

# Nodes
node_x, node_y, node_colors, node_text = [], [], [], []

for node in mst.nodes():
    x, y = pos[node]
    node_x.append(x)
    node_y.append(y)
    node_colors.append(color_map[node])
    node_text.append(node)

node_trace = go.Scatter(
    x=node_x,
    y=node_y,
    mode="markers+text",
    text=node_text,
    textposition="middle center",
    hovertemplate="%{text}<extra></extra>",
    marker=dict(
        size=32,
        color=node_colors,
        line=dict(width=1, color="black")
    )
)

fig_mst = go.Figure(
    data=[edge_trace, node_trace],
    layout=go.Layout(
        title=f"MST – {snapshot_date.date()}",
        template="plotly_white",
        showlegend=False,
        height=700,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False)
    )
)

st.plotly_chart(fig_mst, use_container_width=True)
