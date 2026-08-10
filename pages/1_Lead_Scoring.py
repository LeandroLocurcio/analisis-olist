"""Página de Lead Scoring: performance del modelo + simulador interactivo."""

from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import pandas as pd
import plotly.graph_objects as go
import shap
import streamlit as st
from sklearn.metrics import confusion_matrix, roc_auc_score, roc_curve

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = PROJECT_ROOT / "models" / "xgb_lead_scoring.pkl"

FEATURE_COLS = ["origin", "contact_dayofweek", "lp_freq"]
DAY_NAMES = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

st.set_page_config(page_title="Lead Scoring | Olist Analytics", page_icon="🎯", layout="wide")


@st.cache_resource
def load_model():
    return joblib.load(MODEL_PATH)


@st.cache_data
def load_features() -> pd.DataFrame:
    """Reproduce notebooks/02_lead_scoring.ipynb (secciones 2-4): acota a leads de 2018
    (antes de esa fecha el dataset no llega a registrar conversiones) y arma las features."""
    mql = pd.read_csv(PROJECT_ROOT / "data" / "olist_marketing_qualified_leads_dataset.csv")
    closed_deals = pd.read_csv(PROJECT_ROOT / "data" / "olist_closed_deals_dataset.csv")

    mql = mql.copy()
    mql["converted"] = mql["mql_id"].isin(closed_deals["mql_id"]).astype(int)
    mql["first_contact_date"] = pd.to_datetime(mql["first_contact_date"])
    mql = mql[mql["first_contact_date"] >= "2018-01-01"].copy()

    mql["contact_dayofweek"] = mql["first_contact_date"].dt.dayofweek
    mql["origin"] = mql["origin"].fillna("unknown").astype("category")

    landing_page_freq = mql["landing_page_id"].value_counts()
    mql["lp_freq"] = mql["landing_page_id"].map(landing_page_freq)

    return mql


@st.cache_data
def evaluate_model(_model, mql: pd.DataFrame):
    """Split temporal (train ene-mar / test abr-may 2018), igual que el notebook."""
    test_mask = mql["first_contact_date"] >= "2018-04-01"
    X_test = mql.loc[test_mask, FEATURE_COLS]
    y_test = mql.loc[test_mask, "converted"]

    y_proba = _model.predict_proba(X_test)[:, 1]
    y_pred = _model.predict(X_test)
    auc = roc_auc_score(y_test, y_proba)
    fpr, tpr, _ = roc_curve(y_test, y_proba)
    cm = confusion_matrix(y_test, y_pred)
    return X_test, y_test, y_proba, auc, fpr, tpr, cm


@st.cache_data
def compute_shap(_model, X_test: pd.DataFrame):
    explainer = shap.TreeExplainer(_model)
    return explainer.shap_values(X_test)


model = load_model()
mql = load_features()
X_test, y_test, y_proba, auc, fpr, tpr, cm = evaluate_model(model, mql)
base_rate = mql["converted"].mean()

st.title("🎯 Lead Scoring")
st.markdown(
    "Clasificador XGBoost que prioriza los **Marketing Qualified Leads (MQL)** según su "
    "probabilidad de convertirse en seller. Target: conversión "
    f"(~{base_rate:.1%} de los {len(mql):,} MQLs de 2018 convierten). "
    "Detalle completo en `notebooks/02_lead_scoring.ipynb`."
)
st.info(
    "**Nota metodológica:** la primera versión de este modelo usaba el mes de contacto "
    "como feature y llegaba a un AUC de 0.718 — pero resultó ser un artefacto de censura "
    "temporal (el dataset no registra ninguna conversión antes de dic-2017, no estacionalidad "
    "real). Corregido: se acota a leads de 2018 y se usa un split temporal (train ene-mar, "
    "test abr-may). El AUC baja a 0.647, pero ahora mide algo real — ver sección 2 del notebook."
)

st.divider()

st.subheader("Performance del modelo (test set)")
col1, col2, col3 = st.columns(3)
col1.metric("AUC-ROC (test, abr-may 2018)", f"{auc:.3f}")
col2.metric("Filas de test", f"{len(y_test):,}")
col3.metric("Tasa base de conversión (test)", f"{y_test.mean():.1%}")

col_roc, col_cm = st.columns(2)

with col_roc:
    fig_roc = go.Figure()
    fig_roc.add_trace(go.Scatter(x=fpr, y=tpr, mode="lines", name=f"XGBoost (AUC={auc:.3f})"))
    fig_roc.add_trace(
        go.Scatter(x=[0, 1], y=[0, 1], mode="lines", name="Azar (AUC=0.5)", line=dict(dash="dash"))
    )
    fig_roc.update_layout(
        title="Curva ROC", xaxis_title="Falsos Positivos", yaxis_title="Verdaderos Positivos"
    )
    st.plotly_chart(fig_roc, width="stretch")

with col_cm:
    fig_cm = go.Figure(
        data=go.Heatmap(
            z=cm,
            x=["No convierte", "Convierte"],
            y=["No convierte", "Convierte"],
            text=cm,
            texttemplate="%{text}",
            colorscale="Blues",
        )
    )
    fig_cm.update_layout(
        title="Matriz de Confusión (umbral 0.5)",
        xaxis_title="Predicho",
        yaxis_title="Real",
        yaxis=dict(autorange="reversed"),
    )
    st.plotly_chart(fig_cm, width="stretch")

st.subheader("Interpretabilidad (SHAP)")
shap_values = compute_shap(model, X_test)
fig_shap = plt.figure()
shap.summary_plot(shap_values, X_test, show=False)
st.pyplot(fig_shap)
plt.close(fig_shap)
st.caption(
    "Orden de importancia: `lp_freq` > `origin` > `contact_dayofweek` — sin el ruido de "
    "`contact_month`, la popularidad de la landing page y el canal de origen quedan como las "
    "señales dominantes."
)

st.divider()

st.subheader("Simulador: ¿qué tan prometedor es este lead?")
lp_freq_min = int(mql["lp_freq"].min())
lp_freq_max = int(mql["lp_freq"].max())
lp_freq_median = int(mql["lp_freq"].median())
origin_options = sorted(mql["origin"].cat.categories.tolist())

with st.form("lead_predictor"):
    c1, c2, c3 = st.columns(3)
    origin_input = c1.selectbox("Canal de origen", origin_options)
    day_input = c2.selectbox("Día de contacto", DAY_NAMES)
    lp_freq_input = c3.slider(
        "Popularidad de la landing page",
        min_value=lp_freq_min,
        max_value=lp_freq_max,
        value=lp_freq_median,
        help=(
            "Frecuencia histórica de la landing page (cuántos leads llegaron por esa misma "
            "página). Valores altos = página muy transitada; bajos = de nicho."
        ),
    )
    submitted = st.form_submit_button("Predecir probabilidad de conversión")

if submitted:
    lead_input = pd.DataFrame(
        {
            "origin": pd.Categorical([origin_input], categories=mql["origin"].cat.categories),
            "contact_dayofweek": [DAY_NAMES.index(day_input)],
            "lp_freq": [lp_freq_input],
        }
    )
    proba = model.predict_proba(lead_input)[0, 1]

    st.metric(
        "Probabilidad de conversión",
        f"{proba:.1%}",
        delta=f"{(proba - base_rate) / base_rate:+.0%} vs. tasa base ({base_rate:.1%})",
    )
    if proba >= base_rate * 1.5:
        st.success("Lead de alta prioridad: bastante por encima de la tasa base de conversión.")
    elif proba >= base_rate * 0.75:
        st.info("Lead dentro del rango típico de conversión.")
    else:
        st.warning("Lead de baja prioridad: por debajo de la tasa base de conversión.")
