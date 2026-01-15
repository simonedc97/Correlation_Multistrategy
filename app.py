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
    df = df.set_index(df.columns[0]).sort_index()
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
st.subheader("🕸️ Correlation Radar")

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
# MST – CON REFERENCE NODE (CORRETTO)
# --------------------------------------------------
st.subheader("🌳 Minimum Spanning Tree (with reference)")

snapshot = df.loc[snapshot_date, selected_series]

G = nx.Graph()

# ---- reference edges (radiali)
for asset, rho in snapshot.items():
    d_ref = np.sqrt(2 * (1 - rho))
    G.add_edge(reference_asset, asset, weight=d_ref)

# ---- asset-asset edges (similarità di esposizione)
for i in snapshot.index:
    for j in snapshot.index:
        if i < j:
            d = abs(snapshot[i] - snapshot[j])
            G.add_edge(i, j, weight=d)

# ---- MST
mst = nx.minimum_spanning_tree(G)

# ---- layout
pos = nx.spring_layout(mst, seed=42)

# --------------------------------------------------
# EDGES
# --------------------------------------------------
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
    line=dict(color="gray", width=1.5),
    hoverinfo="none"
)

# --------------------------------------------------
# NODES
# --------------------------------------------------
node_x, node_y, node_size, node_color, node_text = [], [], [], [], []

for node in mst.nodes():

    x, y = pos[node]
    node_x.append(x)
    node_y.append(y)

    if node == reference_asset:
        node_size.append(70)
        node_color.append("black")
        label = f"<b>{node}</b>"
    else:
        node_size.append(48)
        node_color.append(color_map[node])
        label = f"<b>{node}</b><br>ρ={snapshot[node]:.2f}"

    node_text.append(label)

node_trace = go.Scatter(
    x=node_x,
    y=node_y,
    mode="markers+text",
    text=node_text,
    textposition="middle center",
    hoverinfo="none",
    marker=dict(
        size=node_size,
        color=node_color,
        line=dict(width=2, color="black")
    ),
    textfont=dict(
        size=14,
        color="white"
    )
)

# --------------------------------------------------
# FIGURE
# --------------------------------------------------
fig_mst = go.Figure(
    data=[edge_trace, node_trace],
    layout=go.Layout(
        title=(
            f"MST with reference: {reference_asset}<br>"
            f"<sup>Distances: |ρᵢ−ρⱼ| (asset) · √(2(1−ρ)) (reference)</sup>"
        ),
        template="plotly_white",
        showlegend=False,
        height=800,
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
).rename(columns={"mean": "Mean", "min": "Min", "max": "Max"})

st.dataframe(
    stats_df.style.format("{:.2f}%"),
    use_container_width=True
)
