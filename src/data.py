"""
ETL: carga y consolidacion de las tablas crudas de Olist.

Arma dos datasets de salida:
  - order_items_full: una fila por (order_id, order_item_id), con datos de
    cliente, vendedor, producto, pago y review ya cruzados.
  - seller_features: una fila por seller_id, con metricas de comportamiento
    agregadas (para el eje de segmentacion).

order_items_full incluye tambien distance_km: la distancia haversine (en
linea recta, sobre la superficie terrestre) entre seller y customer.

Uso:
    from src.data import build_datasets
    order_items, seller_features = build_datasets()
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

RAW_DIR = Path(__file__).resolve().parents[1] / "data"
PROCESSED_DIR = RAW_DIR / "processed"

EARTH_RADIUS_KM = 6371

RAW_FILES = {
    "customers": "olist_customers_dataset.csv",
    "geolocation": "olist_geolocation_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "order_payments": "olist_order_payments_dataset.csv",
    "order_reviews": "olist_order_reviews_dataset.csv",
    "orders": "olist_orders_dataset.csv",
    "products": "olist_products_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "category_translation": "product_category_name_translation.csv",
    "closed_deals": "olist_closed_deals_dataset.csv",
    "mql": "olist_marketing_qualified_leads_dataset.csv",
}


def load_raw_tables(data_dir: Path = RAW_DIR) -> dict[str, pd.DataFrame]:
    """Carga los 11 CSVs crudos de Olist en un diccionario de DataFrames."""
    return {name: pd.read_csv(data_dir / filename) for name, filename in RAW_FILES.items()}


def aggregate_geolocation(geolocation: pd.DataFrame) -> pd.DataFrame:
    """Colapsa geolocation a una fila por zip_code_prefix (promedio de lat/lng).

    La tabla cruda trae ~1M filas para ~19k prefijos unicos (varias
    coordenadas por prefijo, de distintos puntos dentro de la misma zona
    postal). Para poder cruzarla 1 a 1 con customers/sellers hay que
    agregarla primero.
    """
    return (
        geolocation.groupby("geolocation_zip_code_prefix")
        .agg(
            lat=("geolocation_lat", "mean"),
            lng=("geolocation_lng", "mean"),
            city=("geolocation_city", "first"),
            state=("geolocation_state", "first"),
        )
        .reset_index()
        .rename(columns={"geolocation_zip_code_prefix": "zip_code_prefix"})
    )


def haversine_distance(
    lat1: pd.Series, lng1: pd.Series, lat2: pd.Series, lng2: pd.Series
) -> pd.Series:
    """Distancia en km sobre la superficie terrestre entre dos puntos (vectorizado).

    lat/lng en grados decimales. Filas con algun valor faltante devuelven NaN.
    """
    lat1, lng1, lat2, lng2 = (np.radians(x) for x in (lat1, lng1, lat2, lng2))
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlng / 2) ** 2
    return EARTH_RADIUS_KM * 2 * np.arcsin(np.sqrt(a))


def _merge_geo(df: pd.DataFrame, geo: pd.DataFrame, side: str) -> pd.DataFrame:
    """Suma lat/lng agregados de geolocation a df, para 'customer' o 'seller'."""
    zip_col = f"{side}_zip_code_prefix"
    geo_renamed = geo.rename(
        columns={
            "zip_code_prefix": zip_col,
            "lat": f"{side}_lat",
            "lng": f"{side}_lng",
            "city": f"{side}_geo_city",
            "state": f"{side}_geo_state",
        }
    )
    return df.merge(geo_renamed, on=zip_col, how="left")


def _aggregate_payments(order_payments: pd.DataFrame) -> pd.DataFrame:
    """Un pedido puede tener varios pagos (cuotas, vouchers combinados). Se agrega a nivel orden."""
    return (
        order_payments.groupby("order_id")
        .agg(
            payment_value=("payment_value", "sum"),
            payment_installments=("payment_installments", "max"),
            payment_type=("payment_type", "first"),
        )
        .reset_index()
    )


def _aggregate_reviews(order_reviews: pd.DataFrame) -> pd.DataFrame:
    """Un pedido puede tener mas de una review (recompra); nos quedamos con la mas reciente."""
    return (
        order_reviews.sort_values("review_answer_timestamp")
        .drop_duplicates(subset="order_id", keep="last")[["order_id", "review_score"]]
    )


def build_order_items(tables: dict[str, pd.DataFrame], geo: pd.DataFrame) -> pd.DataFrame:
    """Arma el dataset consolidado a nivel order_item.

    Une order_items con orders, customers, sellers, productos (+ categoria
    traducida), pagos y reviews agregados a nivel orden, y las coordenadas
    de customer/seller.
    """
    products = tables["products"].merge(
        tables["category_translation"], on="product_category_name", how="left"
    )

    df = tables["order_items"].merge(tables["orders"], on="order_id", how="left")
    df = df.merge(tables["customers"], on="customer_id", how="left")
    df = df.merge(tables["sellers"], on="seller_id", how="left")
    df = df.merge(products, on="product_id", how="left")
    df = df.merge(_aggregate_payments(tables["order_payments"]), on="order_id", how="left")
    df = df.merge(_aggregate_reviews(tables["order_reviews"]), on="order_id", how="left")

    df = _merge_geo(df, geo, "customer")
    df = _merge_geo(df, geo, "seller")

    df["distance_km"] = haversine_distance(
        df["customer_lat"], df["customer_lng"], df["seller_lat"], df["seller_lng"]
    )

    return df


def build_seller_features(order_items_full: pd.DataFrame) -> pd.DataFrame:
    """Agrega order_items_full a nivel seller: una fila por vendedor con metricas de comportamiento."""
    return (
        order_items_full.groupby("seller_id")
        .agg(
            seller_state=("seller_state", "first"),
            n_orders=("order_id", "nunique"),
            n_items=("order_item_id", "count"),
            n_categories=("product_category_name_english", "nunique"),
            revenue=("price", "sum"),
            avg_ticket=("price", "mean"),
            avg_freight=("freight_value", "mean"),
            avg_review_score=("review_score", "mean"),
            avg_distance_km=("distance_km", "mean"),
        )
        .reset_index()
    )


def build_datasets(
    data_dir: Path = RAW_DIR, save: bool = True
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Corre el ETL completo y devuelve (order_items_full, seller_features)."""
    tables = load_raw_tables(data_dir)
    geo = aggregate_geolocation(tables["geolocation"])

    order_items_full = build_order_items(tables, geo)
    seller_features = build_seller_features(order_items_full)

    if save:
        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        order_items_full.to_parquet(PROCESSED_DIR / "order_items_full.parquet", index=False)
        seller_features.to_parquet(PROCESSED_DIR / "seller_features.parquet", index=False)

    return order_items_full, seller_features


if __name__ == "__main__":
    order_items_full, seller_features = build_datasets()
    print(f"order_items_full: {order_items_full.shape}")
    print(f"seller_features:  {seller_features.shape}")
