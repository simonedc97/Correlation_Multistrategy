import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO

st.set_page_config(page_title="Stress Test", layout="wide")

# ======================================================
# CONFIG
# ======================================================

STRESS_LIST_PATH = "StressUtilizzati.xlsx"
STRESS_DATA_PATH = "StressData.xlsx"

# ======================================================
# LOAD STRESS LIST (ORDINATA PER LUNGHEZZA ↓)
# ======================================================

@st.cache_data
def load_stress_list(path):
    df = pd.read_excel(path, usecols=[0])
    return (
        df.iloc[:, 0]
        .dropna()
        .astype(str)
        .str.strip()
        .sort_values(key=lambda x: x.str.len(), ascending=False)
        .tolist()
    )

# ======================================================
# PARSING SHEET NAME (FIX DEFINITIVO)
# ======================================================

def split_sheet_name(sheet_name, stress_list):
    for stress in stress_list:
        suffix = f"_{stress}"
        if sheet_name.endswith(suffix):
            portfolio = sheet_name[:-len(suffix)]
            return portfolio, stress

    st.warning(f"⚠️ Stress non riconosciuto: {sheet_name}")
    return sheet_name, "UNKNOWN"

# ======================================================
# LOAD STRESS DATA (UNICA VERSIONE)
# ======================================================

@st.cache_data
def load_stress_data(path, stress_list):
    xls = pd.ExcelFile(path)
    out = []

    for sheet in xls.sheet_names:
        portfolio, stress = split_sheet_name(sheet, stress_list)

        df = pd.read_excel(xls, sheet_name=sheet)

        df = df.rename(columns={
            df.columns[0]: "Date",
            df.columns[2]: "Scenario",
            df.columns[4]: "StressPnL"
        })

        df["Date"] = pd.to_datetime(df["Date"])
        df["Portfolio"] = portfolio
        df["Stress"] = stress

        out.append(
            df[["Date", "Scenario", "StressPnL", "Portfolio", "Stress"]]
        )

    return pd.concat(out, ignore_index=True)

# ======================================================
# DOWNLOAD UTILITY
# ======================================================

def download_excel(df, name):
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False)
    st.download_button(
        label="📥 Download Excel",
        data=buffer.getvalue(),
        file_name=name,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# ======================================================
# APP
# ======================================================

st.title("Stress Test Analysis")

stress_list = load_stress_list(STRESS_LIST_PATH)
stress_data = load_stress_data(STRESS_DATA_PATH, stress_list)

# ======================================================
# SIDEBAR
# ======================================================

st.sidebar.header("Filtri")

portfolio_sel = st.sidebar.multiselect(
    "Portfolio",
    sorted(stress_data["Portfolio"].unique()),
    default=sorted(stress_data["Portfolio"].unique())
)

stress_sel = st.sidebar.multiselect(
    "Stress",
    sorted(stress_data["Stress"].unique()),
    default=sorted(stress_data["Stress"].unique())
)

df = stress_data[
    stress_data["Portfolio"].isin(portfolio_sel) &
    stress_data["Stress"].isin(stress_sel)
]

# ======================================================
# NOTE
# ======================================================

st.markdown("""
### 📝 Note
- Gli stress vengono riconosciuti **solo** tramite `StressUtilizzati.xlsx`
- Il parsing usa **sempre lo stress più lungo**
- Duplicazioni tipo `E7X / E7X_USDN_REL` **non sono possibili**
""")

# ======================================================
# CONTROLLO PARSING (DEBUG VISIVO)
# ======================================================

with st.expander("🔍 Controllo parsing sheet"):
    st.dataframe(
        df[["Portfolio", "Stress"]]
        .drop_duplicates()
        .sort_values(["Portfolio", "Stress"])
    )

# ======================================================
# AGGREGAZIONE
# ======================================================

agg = (
    df.groupby(["Portfolio", "Stress"], as_index=False)["StressPnL"]
    .sum()
)

# ======================================================
# GRAFICO
# ======================================================

st.subheader("Stress PnL per Portfolio")

fig, ax = plt.subplots(figsize=(12, 6))

for stress in agg["Stress"].unique():
    subset = agg[agg["Stress"] == stress]
    ax.bar(
        subset["Portfolio"],
        subset["StressPnL"],
        label=stress
    )

ax.set_ylabel("Stress PnL")
ax.legend()
ax.grid(axis="y")

st.pyplot(fig)

# ======================================================
# DOWNLOAD
# ======================================================

st.subheader("Download dati")
download_excel(df, "stress_data_filtered.xlsx")
download_excel(agg, "stress_pnl_aggregated.xlsx")
