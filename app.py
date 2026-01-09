import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# ---------------------------------------------------
# Funzione di caricamento e pulizia
# ---------------------------------------------------
@st.cache_data
def load_corr_data(path):
    df = pd.read_excel(path, sheet_name="Correlation Clean")
    df.iloc[:, 0] = pd.to_datetime(df.iloc[:, 0])
    df = df.set_index(df.columns[0])
    df = df.sort_index()
    return df


# ---------------------------------------------------
# Caricamento dati
# ---------------------------------------------------
corrEGQ = load_corr_data("corrEGQ.xlsx")
corrE7U = load_corr_data("corrE7X.xlsx")

# ---------------------------------------------------
# Sidebar – selezione grafico
# ---------------------------------------------------
st.sidebar.title("Selezione grafico")

chart_type = st.sidebar.selectbox(
    "Scegli il grafico",
    ["EGQ vs Index and Cash", "E7X vs Funds"]
)

# ---------------------------------------------------
# Switch dataset
# ---------------------------------------------------
if chart_type == "EGQ vs Index and Cash":
    df = corrEGQ.copy()
    title = "EGQ vs Index and Cash"
else:
    df = corrE7X.copy()
    title = "E7X vs Funds"

# ---------------------------------------------------
# Selezione date (solo quelle disponibili)
# ---------------------------------------------------
available_dates = df.index.unique()

start_date = st.sidebar.selectbox(
    "Data inizio",
    available_dates,
    index=0
)

end_date = st.sidebar.selectbox(
    "Data fine",
    available_dates,
    index=len(available_dates) - 1
)

df = df.loc[start_date:end_date]

# ---------------------------------------------------
# Selezione linee
# ---------------------------------------------------
available_series = df.columns.tolist()

selected_series = st.sidebar.multiselect(
    "Seleziona le linee da visualizzare",
    available_series,
    default=available_series
)

# ---------------------------------------------------
# Plot
# ---------------------------------------------------
st.title(title)

if len(selected_series) == 0:
    st.warning("Seleziona almeno una linea.")
else:
    fig, ax = plt.subplots(figsize=(10, 5))

    for col in selected_series:
        ax.plot(df.index, df[col], label=col)

    ax.set_xlabel("Date")
    ax.set_ylabel("Correlation")
    ax.legend()
    ax.grid(True)

    st.pyplot(fig)
