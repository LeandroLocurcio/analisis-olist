"""Página de Segmentación de Sellers: clusters PCA + K-Means interactivos."""

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data" / "processed"

LOG_COLS = ["n_orders", "revenue", "avg_ticket", "avg_freight", "n_categories"]
FEATURE_COLS = LOG_COLS + ["avg_review_score", "avg_distance_km"]

CLUSTER_INFO = {
    0: {
        "nombre": "En riesgo",
        "descripcion": (
            "Bajo volumen y revenue, catálogo angosto y **review promedio 1.93** — muy por "
            "debajo de cualquier otro grupo. Único cluster con problema de calidad, no de "
            "tamaño: justifica revisar logística/producto/atención antes de invertir en "
            "hacerlos crecer."
        ),
    },
    1: {
        "nombre": "Pequeños y confiables",
        "descripcion": (
            "El grupo más grande. Bajo volumen y revenue, pero la **mejor review del dataset "
            "(4.46)** y la distancia más corta a sus compradores. Base sana del marketplace, "
            "candidatos naturales para programas de crecimiento."
        ),
    },
    2: {
        "nombre": "Power sellers",
        "descripcion": (
            "Volumen muy alto (~17x el resto), el revenue más alto por lejos y el catálogo "
            "más amplio, con buena review. Cuentas clave: prioridad de retención."
        ),
    },
    3: {
        "nombre": "Nicho premium",
        "descripcion": (
            "Volumen moderado pero el **ticket promedio más alto por lejos**, catálogo "
            "angosto, buena review y la distancia más larga a sus compradores — el flete alto "
            "es la fricción más visible para este grupo."
        ),
    },
}

st.set_page_config(page_title="Segmentación de Sellers | Olist Analytics", page_icon="🧩", layout="wide")


@st.cache_data
def load_seller_features() -> pd.DataFrame:
    return pd.read_parquet(DATA_DIR / "seller_features.parquet")


@st.cache_data
def segment_sellers(seller_features: pd.DataFrame) -> pd.DataFrame:
    """Reproduce el pipeline de notebooks/03_seller_segmentation.ipynb (mismo random_state)."""
    df = seller_features.dropna(subset=["avg_review_score", "avg_distance_km"]).copy()

    X = df[FEATURE_COLS].copy()
    for col in LOG_COLS:
        X[col] = np.log1p(X[col])

    X_scaled = StandardScaler().fit_transform(X)

    pca = PCA(n_components=2, random_state=42)
    coords = pca.fit_transform(X_scaled)
    df["pc1"] = coords[:, 0]
    df["pc2"] = coords[:, 1]

    kmeans = KMeans(n_clusters=4, random_state=42, n_init=10)
    df["cluster"] = kmeans.fit_predict(X_scaled)
    df["cluster_nombre"] = df["cluster"].map(lambda c: CLUSTER_INFO[c]["nombre"])

    return df


seller_features = load_seller_features()
df = segment_sellers(seller_features)

st.title("🧩 Segmentación de Sellers")
st.markdown(
    f"PCA + K-Means (K=4) sobre {len(df):,} sellers, a partir de volumen, revenue, ticket "
    "promedio, flete, reviews, distancia a compradores y variedad de catálogo. "
    "Detalle completo en `notebooks/03_seller_segmentation.ipynb`."
)

st.divider()

col_scatter, col_profile = st.columns([3, 2])

with col_scatter:
    st.subheader("Sellers proyectados en PCA")
    fig = px.scatter(
        df,
        x="pc1",
        y="pc2",
        color="cluster_nombre",
        hover_data={
            "seller_id": True,
            "n_orders": True,
            "revenue": ":.0f",
            "avg_review_score": ":.2f",
            "pc1": False,
            "pc2": False,
        },
        labels={"pc1": "PC1", "pc2": "PC2", "cluster_nombre": "Cluster"},
        opacity=0.55,
    )
    st.plotly_chart(fig, width="stretch")

with col_profile:
    st.subheader("Perfil por cluster")
    profile = df.groupby("cluster")[FEATURE_COLS].mean().round(2)
    sizes = df["cluster"].value_counts().sort_index()
    for cluster_id, info in CLUSTER_INFO.items():
        with st.expander(f"**{cluster_id} — {info['nombre']}** ({sizes[cluster_id]} sellers)"):
            st.markdown(info["descripcion"])
            st.dataframe(
                profile.loc[[cluster_id]].T.rename(columns={cluster_id: "promedio"}),
                width="stretch",
            )

st.divider()

st.subheader("Buscar un seller")
seller_id_input = st.selectbox("seller_id", sorted(df["seller_id"].unique()))
seller_row = df[df["seller_id"] == seller_id_input].iloc[0]
cluster_id = int(seller_row["cluster"])

st.markdown(
    f"**{seller_id_input}** cae en el cluster **{cluster_id} — "
    f"{CLUSTER_INFO[cluster_id]['nombre']}**."
)
metric_cols = st.columns(len(FEATURE_COLS))
for col, feature in zip(metric_cols, FEATURE_COLS):
    cluster_avg = profile.loc[cluster_id, feature]
    col.metric(
        feature,
        f"{seller_row[feature]:.2f}",
        delta=f"{seller_row[feature] - cluster_avg:+.2f} vs. cluster",
    )
