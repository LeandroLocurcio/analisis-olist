# Review del proyecto — backlog accionable

Revisión externa del repo (agosto 2026). Cada punto es una tarea independiente,
ordenada por prioridad. Los hallazgos numéricos ya fueron verificados corriendo
código contra los datos reales; no hace falta re-verificarlos, pero sí hay que
implementar los arreglos.

**Convención:** trabajar de a un punto por vez, commitear con mensaje
convencional (`fix:`, `feat:`, `docs:`, `test:`), y actualizar el README y el
roadmap cuando corresponda.

---

## P1 — Selección de hiperparámetros sobre el test set

**Archivo:** `notebooks/02_lead_scoring.ipynb`, sección 4 (celda del `param_grid`).

**Problema:** el loop recorre 36 combinaciones, calcula `auc_test` para cada una,
ordena por `auc_test` y se queda con la mejor. Después la sección 6 reporta ese
mismo `auc_test` (0.719) como performance del modelo. Eso es selección de modelo
sobre el conjunto de test: la métrica queda optimistamente sesgada y ya no existe
un holdout limpio.

**Arreglo:** reemplazar el loop manual por `GridSearchCV` con
`StratifiedKFold(n_splits=5, shuffle=True, random_state=42)` y
`scoring='roc_auc'`, ajustado **solo sobre train**. Reportar el AUC de CV como
métrica de selección y tocar el test una única vez, al final, para la métrica
que se publica. Mantener el mismo grid (`max_depth` [2,3,4],
`min_child_weight` [3,5,10,20], `reg_lambda` [1,5,10]) y el `scale_pos_weight`
calculado sobre train.

Actualizar el texto narrativo de la sección 4, que hoy justifica la búsqueda
mirando el gap train/test.

---

## P2 — `contact_month` es un artefacto de censura, no estacionalidad

**Archivos:** `notebooks/02_lead_scoring.ipynb` (secciones 2, 7 y 9), `README.md`,
`pages/1_Lead_Scoring.py`.

**Problema (verificado con los datos):**

- Los MQL van de **2017-06-14 a 2018-05-31** (12 meses exactos).
- `won_date` en `olist_closed_deals_dataset.csv` arranca recién el **2017-12-05**.
- Tasa de conversión por mes de primer contacto: jul-2017 **0.8%**, ago-2017 2.3%,
  nov-2017 4.0%, ene-2018 **13.3%**, feb-2018 14.5%, mar-2018 14.2%,
  abr-2018 13.5%, may-2018 10.0%.

Como la ventana es de exactamente 12 meses, `contact_month` ∈ {1..5} equivale a
"2018" y {6..12} a "2017". El modelo no aprendió estacionalidad comercial:
aprendió que los leads de 2017 casi no convierten, lo cual pasa porque el dataset
no registra deals ganados antes de diciembre de 2017. Es censura del período de
recolección, no señal de negocio. La conclusión actual del README
("la estacionalidad del contacto pesa más que el canal de origen") no se sostiene.

**Números de referencia** (reentrenando con los mismos hiperparámetros:
`max_depth=2, min_child_weight=20, reg_lambda=10`):

| Setup | AUC test |
|---|---|
| Actual del notebook (split aleatorio, 8000 leads) | 0.715 |
| Sin `contact_month` | 0.683 |
| Solo leads de 2018, split aleatorio | 0.657 |
| Solo 2018 + split temporal (train ene–mar / test abr–may) | **0.666** |

**Arreglo:**

1. Acotar el universo a los leads con la ventana de registro de conversiones
   abierta (first_contact >= 2018-01-01), documentando por qué.
2. Cambiar el split aleatorio por un **split temporal** (train ene–mar 2018,
   test abr–may 2018). Esto además es lo correcto conceptualmente: en producción
   se puntúan leads futuros con un modelo entrenado en el pasado.
3. Reemplazar `contact_month` por `contact_dayofweek` + alguna feature que no
   codifique el año, o dejar `contact_month` pero documentar explícitamente que
   dentro de la ventana acotada ya no actúa como proxy del año.
4. Agregar una sección narrativa contando el hallazgo. **Es el punto más
   valioso del notebook**: "detecté que mi feature más importante era un
   artefacto del período de recolección" vale más que un AUC de 0.72 inflado.
5. Actualizar el AUC publicado en `README.md` (resultados clave), en
   `streamlit_app.py` (bloque "Los 3 ejes del proyecto") y en el caption de SHAP
   de `pages/1_Lead_Scoring.py`.

---

## P3 — Métricas de negocio para el lead scoring

**Archivos:** `notebooks/02_lead_scoring.ipynb` (sección 6),
`pages/1_Lead_Scoring.py`.

**Problema:** el AUC solo no comunica valor. La pregunta del negocio es "si el
equipo comercial llama únicamente al top 20% de los leads priorizados, ¿qué
porcentaje del total de conversiones capturo?".

**Arreglo:**

- Agregar una **curva de lift / ganancia acumulada** (eje X: % de leads
  contactados ordenados por score descendente; eje Y: % de conversiones
  capturadas), más una tabla de `precision@k` y `recall@k` para k = 10%, 20%, 30%.
- Agregar baselines de comparación: `DummyClassifier(strategy='stratified')` y
  `LogisticRegression` con one-hot sobre las mismas features. Reportar los tres
  AUC juntos.
- Llevar la curva de lift también al dashboard, es más persuasiva que la ROC.

---

## P4 — El repo no corre para quien lo clona

- **`reports/figures/data_model.png` no está trackeado**: el `.gitignore` excluye
  `reports/figures/*.png` y el README lo referencia, así que la imagen aparece
  rota en GitLab. Agregar la excepción `!reports/figures/data_model.png` (y
  cualquier otra figura citada en el README).
- **`streamlit_app.py` y `pages/` están sin commitear.** Verificar con
  `git status` y commitearlos.
- **La app crashea al clonar**: lee `data/processed/*.parquet` y los CSVs crudos,
  ninguno versionado. Definir una estrategia y aplicarla — o versionar una muestra
  chica procesada (p. ej. `data/sample/`, unos pocos MB), o que la app consulte
  BigQuery, o que detecte la ausencia de datos y muestre un mensaje con las
  instrucciones de setup en lugar de reventar.
- **`models/xgb_lead_scoring.pkl` está gitignoreado** pero
  `pages/1_Lead_Scoring.py` lo carga con `joblib.load` sin fallback. Mismo
  problema: o se versiona el `.pkl` (pesa poco) o la página lo entrena al vuelo.
- **Falta el archivo `LICENSE`** aunque el README tiene badge de MIT. Agregarlo.

---

## P5 — README desincronizado con el repo

**Archivo:** `README.md`.

- La sección "Estructura del repositorio" dice `notebooks/01_eda.ipynb`; el
  archivo real es `notebooks/EDA_1.ipynb`.
- En `src/` solo lista `download_data.py`; falta `data.py`, que es el corazón
  del ETL.
- El árbol no incluye `streamlit_app.py`, `pages/` ni `sql/`, que ya existen.
- La pregunta 1 de "Problema de negocio" promete identificar leads *"porque van
  a facturar mucho"*, pero el target real es conversión binaria. El notebook
  justifica bien esa decisión (462 de 842 closed deals nunca vendieron nada) —
  hay que trasladar esa justificación al README y corregir la promesa.
- La tabla de metodología menciona "traducción de categorías PT→ES"; verificar
  contra `src/data.py` si es PT→EN y corregir.

---

## P6 — Duplicación de lógica

- **`pages/1_Lead_Scoring.py`** replica por copy-paste el feature engineering de
  `notebooks/02_lead_scoring.ipynb` (fillna de `origin`, `lp_freq`,
  `contact_month`...). Extraer a `src/features.py` una función
  `build_lead_features()` e importarla desde ambos lados. Cuando se aplique P2,
  esto evita que notebook y dashboard queden desincronizados.
- **`notebooks/EDA_1.ipynb`** todavía tiene celdas que cargan CSVs con `pd.read_csv`
  propio en vez de usar `build_datasets()` de `src/data.py`. Migrar las que
  queden (los commits `03eb2d4` y `60243f7` empezaron la migración pero no la
  terminaron).

---

## P7 — Robustez de la segmentación

**Archivo:** `notebooks/03_seller_segmentation.ipynb`.

- El silhouette de 0.244 indica separación débil. Está bien elegir K=4 por
  criterio de negocio, pero conviene dejar explícito en la narrativa que los
  clusters son **una convención de gestión útil, no grupos naturalmente
  separados** en los datos.
- `n_orders` y `revenue` siguen correlacionados aunque se haya sacado `n_items`;
  revisar la matriz de correlación post log-transform y decidir si se justifica.
- Agregar un chequeo de **estabilidad**: correr K-Means con varias semillas
  (o bootstrap sobre subsamples del 80%) y reportar qué porcentaje de sellers
  mantiene su asignación. Un cluster que se desarma al cambiar la semilla no
  sirve para tomar decisiones.
- Documentar cuántos sellers se descartan en el `dropna` de
  `avg_review_score` / `avg_distance_km` y si ese descarte sesga los grupos.

---

## P8 — Tests, CI y Docker

Por orden de retorno para un portfolio:

1. **`tests/test_data.py` con pytest.** Alto impacto y poco trabajo — casi ningún
   portfolio de DS tiene tests. Casos mínimos:
   - `haversine_distance()` entre São Paulo (-23.55, -46.63) y Río (-22.91, -43.17)
     ≈ 357 km (tolerancia ±5 km).
   - `haversine_distance()` de un punto contra sí mismo = 0.
   - Filas con coordenadas faltantes devuelven NaN.
   - **No fan-out en los joins**: `len(order_items_full) == len(order_items)`.
     Esto testea justo la decisión de diseño documentada en CLAUDE.md
     (pagos y reviews pre-agregados a nivel `order_id`).
   - `build_seller_features()` devuelve una fila por `seller_id` único.
   Los tests que necesitan los CSVs deben marcarse con
   `@pytest.mark.skipif(not DATA_DIR.exists())` para que no rompan sin datos.
   Agregar `pytest` a `requirements.txt` (o mejor, un `requirements-dev.txt`).
2. **`.gitlab-ci.yml`** corriendo esos tests en cada push.
3. **Deploy real del Streamlit** (Streamlit Community Cloud). Un link vivo en el
   README vale más que todo lo demás junto para un reclutador no técnico.
   Depende de resolver P4 primero.
4. **Dockerfile + docker-compose** que levante el dashboard. Es el de menor
   retorno de los cuatro, pero cierra el ítem pendiente del roadmap.

---

## P9 — Cerrar el tercer eje: ¿dónde abrir un depósito?

El README plantea la pregunta *"¿Dónde conviene abrir un nuevo depósito?"* pero
ningún notebook la responde. Es la parte más "consultoría" del proyecto y hoy
está prometida y no entregada.

Propuesta: análisis de ubicación óptima que minimice la distancia media
ponderada por volumen de órdenes (o por costo de flete) entre el depósito
candidato y los compradores. Se puede resolver con una grilla de candidatos sobre
los centroides de los estados/ciudades con más volumen, o con un K-Means
ponderado sobre las coordenadas de los compradores. Cerrar con un mapa y una
recomendación concreta en reales ahorrados.

---

## Nota sobre lo que YA está bien (no romper)

- El framing de negocio del README y la estructura de tres ejes.
- `src/data.py`: docstrings claros, funciones chicas, resolución absoluta de paths,
  pre-agregación de pagos y reviews para evitar fan-out.
- La narrativa de los notebooks: las decisiones están justificadas
  (por qué se descartó `landing_page_id` crudo, por qué K=4 con silhouette
  empatado, por qué PCA solo para visualizar y no para clusterizar).
- Reportar resultados negativos con honestidad (correlación distancia ↔ review
  score prácticamente nula). Eso es raro en un portfolio y suma.
- Las queries de `sql/` comentadas explicando la equivalencia con el notebook.
