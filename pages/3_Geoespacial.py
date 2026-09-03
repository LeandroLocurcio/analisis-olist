"""Página Geoespacial: distancia vendedor-comprador vs. flete/review score.

A diferencia de las otras dos páginas (que leen data/processed/ local), esta
consulta en vivo el dataset `olist_dw` en BigQuery, usando exactamente las
queries versionadas en sql/12*.sql y sql/13*.sql.
"""

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from google.api_core.exceptions import GoogleAPIError
from google.auth.exceptions import DefaultCredentialsError
from google.cloud import bigquery
from google.oauth2 import service_account

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SQL_DIR = PROJECT_ROOT / "sql"
BQ_PROJECT = "analisis-olist"

st.set_page_config(page_title="Geoespacial | Olist Analytics", page_icon="🌎", layout="wide")


@st.cache_resource
def get_bq_client() -> bigquery.Client:
    """En Streamlit Cloud usa el service account de st.secrets; en local cae a
    las Application Default Credentials (`gcloud auth application-default login`)."""
    if "gcp_service_account" in st.secrets:
        credentials = service_account.Credentials.from_service_account_info(
            st.secrets["gcp_service_account"]
        )
        return bigquery.Client(project=BQ_PROJECT, credentials=credentials)
    return bigquery.Client(project=BQ_PROJECT)


@st.cache_data(ttl=3600)
def run_query(sql: str) -> pd.DataFrame:
    return get_bq_client().query(sql).to_dataframe()


def read_sql(filename: str) -> str:
    return (SQL_DIR / filename).read_text()


st.title("🌎 Distancia Vendedor-Comprador: Flete y Satisfacción")
st.markdown(
    "Estas queries corren **en vivo contra BigQuery** (`olist_dw`, subido en la "
    "migración cloud del proyecto) — no leen datos locales. "
    "Código fuente en `sql/`."
)

try:
    tab_flete, tab_review = st.tabs(["📦 Distancia vs. Flete", "⭐ Distancia vs. Review Score"])

    with tab_flete:
        sql_corr = read_sql("12a_distancia_vs_flete_correlacion.sql")
        sql_bins = read_sql("12b_distancia_vs_flete_por_bin.sql")

        corr = run_query(sql_corr).iloc[0]
        bins = run_query(sql_bins)

        col1, col2, col3 = st.columns(3)
        col1.metric("Filas usadas", f"{int(corr['n_rows']):,}")
        col2.metric("Correlación de Pearson", f"{corr['pearson_corr']:.3f}")
        col3.metric("Correlación de Spearman", f"{corr['spearman_corr']:.3f}")

        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=bins["distance_mid_km"],
                y=bins["avg_freight_value"],
                mode="lines+markers",
                marker=dict(size=bins["n_orders"].clip(upper=5000) / 200 + 4),
                name="Flete promedio",
            )
        )
        fig.update_layout(
            title="Flete promedio por rango de distancia (tamaño del punto = # órdenes)",
            xaxis_title="Distancia (km, punto medio del bin)",
            yaxis_title="Flete promedio (R$)",
        )
        st.plotly_chart(fig, width="stretch")
        st.caption(
            "La relación es monótona pero no lineal (Spearman >> Pearson): el flete sube "
            "fuerte hasta ~1500km y se aplana después. Los últimos bins tienen pocos pedidos "
            "(ver tamaño del punto) — son ruido, no señal."
        )

        with st.expander("Ver SQL"):
            st.code(sql_corr, language="sql")
            st.code(sql_bins, language="sql")

    with tab_review:
        sql_corr = read_sql("13a_distancia_vs_review_correlacion.sql")
        sql_bins = read_sql("13b_distancia_vs_review_por_bin.sql")

        corr = run_query(sql_corr).iloc[0]
        bins = run_query(sql_bins)

        col1, col2, col3 = st.columns(3)
        col1.metric("Filas usadas", f"{int(corr['n_rows']):,}")
        col2.metric("Correlación de Pearson", f"{corr['pearson_corr']:.3f}")
        col3.metric("Correlación de Spearman", f"{corr['spearman_corr']:.3f}")

        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=bins["distance_mid_km"],
                y=bins["avg_review_score"],
                mode="lines+markers",
                marker=dict(size=bins["n_orders"].clip(upper=5000) / 200 + 4),
                name="Review score promedio",
                line=dict(color="teal"),
            )
        )
        fig.update_layout(
            title="Review score promedio por rango de distancia (tamaño del punto = # órdenes)",
            xaxis_title="Distancia (km, punto medio del bin)",
            yaxis_title="Review score promedio (1-5)",
        )
        st.plotly_chart(fig, width="stretch")
        st.caption(
            "Correlación prácticamente nula: la distancia casi no afecta la satisfacción del "
            "cliente. Lo que sí la afecta (ver sección 10 del EDA) es si el pedido llegó tarde "
            "respecto a lo prometido — un pedido lejano con buena logística puede llegar bien igual."
        )

        with st.expander("Ver SQL"):
            st.code(sql_corr, language="sql")
            st.code(sql_bins, language="sql")

except (GoogleAPIError, DefaultCredentialsError) as e:
    st.error(
        "No se pudo consultar BigQuery. En local, verificá que `gcloud auth "
        "application-default login` esté configurado; en Streamlit Cloud, que el secret "
        f"`gcp_service_account` esté cargado. Además, que el proyecto `{BQ_PROJECT}` tenga "
        "el dataset `olist_dw`.\n\n"
        f"Detalle: {e}"
    )
