import json

file_path = 'd:/analisis-olist/EDA_1.ipynb'

with open(file_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

for cell in nb['cells']:
    if cell['cell_type'] == 'code':
        content = ''.join(cell['source'])
        if "order_items['shipping_limit_date'] = pd.to_datetime" in content and "diff_limit_carrier" in content:
            new_source = [
                "import pandas as pd\n",
                "import matplotlib.pyplot as plt\n",
                "import seaborn as sns\n",
                "\n",
                "# 1. Aseguramos que todas las fechas estén en formato datetime\n",
                "order_items['shipping_limit_date'] = pd.to_datetime(order_items['shipping_limit_date'])\n",
                "orders['order_delivered_carrier_date'] = pd.to_datetime(orders['order_delivered_carrier_date'])\n",
                "orders['order_delivered_customer_date'] = pd.to_datetime(orders['order_delivered_customer_date'])\n",
                "orders['order_estimated_delivery_date'] = pd.to_datetime(orders['order_estimated_delivery_date'])\n",
                "\n",
                "# Como una orden puede tener varios items, tomamos el shipping_limit_date máximo por orden\n",
                "order_items_limit = order_items.groupby('order_id')['shipping_limit_date'].max().reset_index()\n",
                "\n",
                "# 2. Unimos las tablas: orders + límites de envío + reviews + estado del cliente\n",
                "df_times = pd.merge(orders, order_items_limit, on='order_id', how='inner')\n",
                "df_times = pd.merge(df_times, order_reviews[['order_id', 'review_score']], on='order_id', how='left')\n",
                "df_times = pd.merge(df_times, customers[['customer_id', 'customer_state']], on='customer_id', how='left')\n",
                "\n",
                "# ---> Filtramos los valores nulos en las fechas que vamos a utilizar\n",
                "columnas_fechas = [\n",
                "    'shipping_limit_date', \n",
                "    'order_delivered_carrier_date', \n",
                "    'order_delivered_customer_date', \n",
                "    'order_estimated_delivery_date'\n",
                "]\n",
                "# Descartamos las filas donde falta alguna de estas fechas clave (ej: pedidos cancelados o no entregados)\n",
                "df_times.dropna(subset=columnas_fechas, inplace=True)\n",
                "\n",
                "# 3. Calculamos las diferencias de tiempos en Días (Valores POSITIVOS = Llegó antes de la fecha límite/estimada)\n",
                "# Diferencia entre Límite del Seller y Llegada Real al Carrier\n",
                "df_times['diff_limit_carrier'] = (df_times['shipping_limit_date'] - df_times['order_delivered_carrier_date']).dt.total_seconds() / (24*3600)\n",
                "\n",
                "# Diferencia entre Estimación del Cliente y Llegada Real al Cliente\n",
                "df_times['diff_estimated_customer'] = (df_times['order_estimated_delivery_date'] - df_times['order_delivered_customer_date']).dt.total_seconds() / (24*3600)\n"
            ]
            cell['source'] = new_source
            break

with open(file_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)
