"""
Dashboard de Olist: punto de entrada (home / overview).

Junta los 3 ejes analíticos del proyecto (lead scoring, segmentación de
sellers, impacto geoespacial) en una sola app navegable. Cada eje vive en
su propia página dentro de pages/.
"""

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

DATA_DIR = Path(__file__).resolve().parent / "data" / "processed"

st.set_page_config(
    page_title="Olist Analytics",
    page_icon="📊",
    layout="wide",
)


@st.cache_data
def load_processed() -> tuple[pd.DataFrame, pd.DataFrame]:
    order_items_full = pd.read_parquet(DATA_DIR / "order_items_full.parquet")
    seller_features = pd.read_parquet(DATA_DIR / "seller_features.parquet")
    return order_items_full, seller_features


order_items_full, seller_features = load_processed()

st.title("📊 Olist — Análisis de E-Commerce")
st.markdown(
    "Portfolio de Data Science sobre el "
    "[dataset de Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) "
    "(100k órdenes, 3k sellers), con tres ejes analíticos: "
    "**lead scoring**, **segmentación de sellers** y **logística geoespacial**. "
    "Elegí una página en la barra lateral para explorar cada uno en detalle."
)

st.divider()

st.subheader("KPIs generales")

n_orders = order_items_full["order_id"].nunique()
revenue = order_items_full["price"].sum()
avg_review = order_items_full["review_score"].mean()
avg_freight = order_items_full["freight_value"].mean()
avg_distance = order_items_full["distance_km"].mean()
n_sellers = len(seller_features)

col1, col2, col3, col4, col5, col6 = st.columns(6)
col1.metric("Órdenes", f"{n_orders:,}".replace(",", "."))
col2.metric("Revenue total", f"R$ {revenue / 1_000_000:.1f}M")
col3.metric("Sellers", f"{n_sellers:,}".replace(",", "."))
col4.metric("Review promedio", f"{avg_review:.2f} / 5")
col5.metric("Flete promedio", f"R$ {avg_freight:.2f}")
col6.metric("Distancia promedio", f"{avg_distance:.0f} km")

st.divider()

col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Órdenes por estado del comprador")
    orders_by_state = (
        order_items_full.drop_duplicates("order_id")
        .groupby("customer_state")
        .size()
        .sort_values(ascending=False)
        .head(10)
        .reset_index(name="n_orders")
    )
    fig = px.bar(
        orders_by_state,
        x="customer_state",
        y="n_orders",
        labels={"customer_state": "Estado", "n_orders": "Órdenes"},
    )
    st.plotly_chart(fig, width="stretch")

with col_right:
    st.subheader("Los 3 ejes del proyecto")
    st.markdown(
        """
**🎯 Lead Scoring** — XGBoost clasificando qué MQLs conviene perseguir
(AUC 0.647, split temporal sobre leads 2018). Incluye un simulador interactivo de leads.

**🧩 Segmentación de Sellers** — PCA + K-Means sobre comportamiento de
vendedores (4 clusters: en riesgo, pequeños y confiables, power sellers,
nicho premium).

**🌎 Geoespacial** — distancia vendedor-comprador vs. flete y review
score, consultado en vivo contra **BigQuery** (`olist_dw`).
"""
    )

st.caption(
    "Código y notebooks completos en el repo — ver `README.md` para el detalle "
    "de cada eje y el ETL (`src/data.py`)."
)
