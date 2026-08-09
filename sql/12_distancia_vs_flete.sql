-- Sección 12 del EDA (notebooks/EDA_1.ipynb), migrada a BigQuery.
-- Pregunta: ¿la distancia vendedor-comprador explica el valor del flete?
-- Equivalente SQL de: order_items_full[['distance_km','freight_value']].dropna() + .corr()

-- 12.1 Correlación (Pearson y Spearman)
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
  (SELECT COUNT(*) FROM base)                          AS n_rows,
  ROUND((SELECT CORR(distance_km, freight_value) FROM base), 3)         AS pearson_corr,
  ROUND((SELECT CORR(rank_distance, rank_freight) FROM ranked), 3)      AS spearman_corr;

-- 12.2 Flete promedio por rango de distancia (20 bins de ancho igual)
-- Equivalente SQL de: pd.cut(distance_km, bins=20).groupby(...)['freight_value'].mean()
WITH base AS (
  SELECT distance_km, freight_value
  FROM `analisis-olist.olist_dw.order_items_full`
  WHERE distance_km IS NOT NULL AND freight_value IS NOT NULL
),
bounds AS (
  SELECT MIN(distance_km) AS min_dist, MAX(distance_km) AS max_dist
  FROM base
),
binned AS (
  SELECT
    b.freight_value,
    bd.min_dist,
    (bd.max_dist - bd.min_dist) / 20 AS bin_width,
    LEAST(
      CAST(FLOOR((b.distance_km - bd.min_dist) / ((bd.max_dist - bd.min_dist) / 20)) AS INT64),
      19
    ) AS bin_index
  FROM base b
  CROSS JOIN bounds bd
)
SELECT
  bin_index,
  ROUND(min_dist + bin_width * (bin_index + 0.5), 1) AS distance_mid_km,
  COUNT(*)                     AS n_orders,
  ROUND(AVG(freight_value), 2) AS avg_freight_value
FROM binned
GROUP BY bin_index, min_dist, bin_width
ORDER BY bin_index;
