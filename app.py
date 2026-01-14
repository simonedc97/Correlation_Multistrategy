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
    reference_asset = "EGQ"
else:
    df = corrE7X.copy()
    chart_title = "E7X vs Funds"
    reference_asset = "E7X"

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
# COLOR MAP
# --------------------------------------------------
palette = qualitative.Plotly
color_map = {
    serie: palette[i % len(palette)]
    for i, serie in enumerate(selected_series)
}

# Colore dedicato per il reference asset
reference_color = "black"

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
st.subheader("🕸️ Correlation Radar")

snapshot_date = df.index.max()

snapshot = df.loc[snapshot_date, selected_series] * 100
mean_corr = df[selected_series].mean() * 100

fig_radar = go.Figure()

fig_radar.add_trace(
    go.Scatterpolar(
        r=snapshot.values,
        theta=snapshot.index,
        name=f"End date ({snapshot_date.date()})",
        line=dict(width=3)
    )
)

fig_radar.add_trace(
    go.Scatterpolar(
        r=mean_corr.values,
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
# MST – CON REFERENCE ASSET (NON STRUTTURALE)
# --------------------------------------------------
st.subheader("🌳 Minimum Spanning Tree")

# Correlation & distance matrix
corrl = df[selected_series].corr()
distances = np.sqrt(2 * (1 - corrl))

# Build graph
G = nx.Graph()
for i in corrl.index:
    for j in corrl.columns:
        if i < j:
            G.add_edge(i, j, weight=distances.loc[i, j])

mst = nx.minimum_spanning_tree(G, weight="weight")

# Layout MST
pos = nx.spring_layout(mst, seed=42)

# -----------------
# Reference asset position (centro)
# -----------------
pos_ref = np.array([0.0, 0.0])

# -----------------
# MST edges
# -----------------
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

# -----------------
# Reference edges (NON MST)
# -----------------
ref_edge_x, ref_edge_y = [], []

for node in mst.nodes():
    x, y = pos[node]
    ref_edge_x += [pos_ref[0], x, None]
    ref_edge_y += [pos_ref[1], y, None]

ref_edge_trace = go.Scatter(
    x=ref_edge_x,
    y=ref_edge_y,
    mode="lines",
    line=dict(color="lightgray", width=1, dash="dot"),
    hoverinfo="none"
)

# -----------------
# MST nodes
# -----------------
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
    textfont=dict(size=12, color="black"),
    marker=dict(
        size=32,
        color=node_colors,
        line=dict(width=1, color="black")
    )
)

# -----------------
# Reference node
# -----------------
ref_node_trace = go.Scatter(
    x=[pos_ref[0]],
    y=[pos_ref[1]],
    mode="markers+text",
    text=[reference_asset],
    textposition="middle center",
    hovertemplate=f"{reference_asset} (reference)<extra></extra>",
    textfont=dict(size=14, color="white"),
    marker=dict(
        size=42,
        color=reference_color,
        line=dict(width=2, color="black")
    )
)

fig_mst = go.Figure(
    data=[
        edge_trace,
        ref_edge_trace,
        node_trace,
        ref_node_trace
    ],
    layout=go.Layout(
        title=(
            f"MST – {snapshot_date.date()}<br>"
            f"<sup>Distances conditional on {reference_asset} "
        ),
        template="plotly_white",
        showlegend=False,
        height=750,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False)
    )
)

st.plotly_chart(fig_mst, use_container_width=True)

# --------------------------------------------------
# Summary statistics
# --------------------------------------------------
st.subheader("📊 Summary statistics")

stats_df = (
    df[selected_series]
    .agg(["mean", "min", "max"])
    .T * 100
)

stats_df = stats_df.rename(
    columns={
        "mean": "Mean",
        "min": "Min",
        "max": "Max"
    }
)

st.dataframe(
    stats_df.style.format("{:.2f}%"),
    use_container_width=True
)
