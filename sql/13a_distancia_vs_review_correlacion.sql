-- Sección 13 del EDA (notebooks/EDA_1.ipynb), migrada a BigQuery.
-- Pregunta: ¿la distancia vendedor-comprador afecta la satisfacción del cliente?
-- Equivalente SQL de: order_items_full[['distance_km','review_score']].dropna() + .corr()
WITH base AS (
  SELECT distance_km, review_score
  FROM `analisis-olist.olist_dw.order_items_full`
  WHERE distance_km IS NOT NULL AND review_score IS NOT NULL
),
ranked AS (
  SELECT
    RANK() OVER (ORDER BY distance_km)  AS rank_distance,
    RANK() OVER (ORDER BY review_score) AS rank_review
  FROM base
)
SELECT
  (SELECT COUNT(*) FROM base)                                  AS n_rows,
  ROUND((SELECT CORR(distance_km, review_score) FROM base), 3) AS pearson_corr,
  ROUND((SELECT CORR(rank_distance, rank_review) FROM ranked), 3) AS spearman_corr;
