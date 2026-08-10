-- Sección 12 del EDA (notebooks/EDA_1.ipynb), migrada a BigQuery.
-- Pregunta: ¿la distancia vendedor-comprador explica el valor del flete?
-- Equivalente SQL de: order_items_full[['distance_km','freight_value']].dropna() + .corr()
--
-- Spearman se calcula como el Pearson de los rangos, porque BigQuery no
-- tiene una función CORR_SPEARMAN nativa.
WITH base AS (
  SELECT distance_km, freight_value
  FROM `analisis-olist.olist_dw.order_items_full`
  WHERE distance_km IS NOT NULL AND freight_value IS NOT NULL
),
ranked AS (
  SELECT
    RANK() OVER (ORDER BY distance_km)   AS rank_distance,
    RANK() OVER (ORDER BY freight_value) AS rank_freight
  FROM base
)
SELECT
  (SELECT COUNT(*) FROM base)                                     AS n_rows,
  ROUND((SELECT CORR(distance_km, freight_value) FROM base), 3)    AS pearson_corr,
  ROUND((SELECT CORR(rank_distance, rank_freight) FROM ranked), 3) AS spearman_corr;
