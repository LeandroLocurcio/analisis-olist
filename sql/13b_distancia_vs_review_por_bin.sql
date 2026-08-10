-- Sección 13 del EDA (notebooks/EDA_1.ipynb), migrada a BigQuery.
-- Review score promedio por rango de distancia (20 bins de ancho igual).
-- Equivalente SQL de: pd.cut(distance_km, bins=20).groupby(...)['review_score'].mean()
WITH base AS (
  SELECT distance_km, review_score
  FROM `analisis-olist.olist_dw.order_items_full`
  WHERE distance_km IS NOT NULL AND review_score IS NOT NULL
),
bounds AS (
  SELECT MIN(distance_km) AS min_dist, MAX(distance_km) AS max_dist
  FROM base
),
binned AS (
  SELECT
    b.review_score,
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
  COUNT(*)                    AS n_orders,
  ROUND(AVG(review_score), 2) AS avg_review_score
FROM binned
GROUP BY bin_index, min_dist, bin_width
ORDER BY bin_index;
