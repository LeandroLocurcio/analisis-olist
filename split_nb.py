import json

file_path = 'd:/analisis-olist/EDA_1.ipynb'

with open(file_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

# Find the target cell
target_idx = -1
for i, cell in enumerate(nb['cells']):
    if cell['cell_type'] == 'code':
        content = ''.join(cell['source'])
        if "order_items['shipping_limit_date'] = pd.to_datetime" in content and "diff_limit_carrier" in content:
            target_idx = i
            break

if target_idx != -1:
    print(f"Found target cell at index {target_idx}")
    
    def m(src):
        return {"cell_type": "markdown", "metadata": {}, "source": [src + "\n"]}
    
    def c(src_lines):
        return {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": [line + "\n" if not line.endswith('\n') else line for line in src_lines]}
    
    # Split the lines
    
    code_1 = [
        "import pandas as pd",
        "import matplotlib.pyplot as plt",
        "import seaborn as sns",
        "",
        "# 1. Aseguramos que todas las fechas estén en formato datetime",
        "order_items['shipping_limit_date'] = pd.to_datetime(order_items['shipping_limit_date'])",
        "orders['order_delivered_carrier_date'] = pd.to_datetime(orders['order_delivered_carrier_date'])",
        "orders['order_delivered_customer_date'] = pd.to_datetime(orders['order_delivered_customer_date'])",
        "orders['order_estimated_delivery_date'] = pd.to_datetime(orders['order_estimated_delivery_date'])",
        "",
        "# Como una orden puede tener varios items, tomamos el shipping_limit_date máximo por orden",
        "order_items_limit = order_items.groupby('order_id')['shipping_limit_date'].max().reset_index()",
        "",
        "# 2. Unimos las tablas: orders + límites de envío + reviews + estado del cliente",
        "df_times = pd.merge(orders, order_items_limit, on='order_id', how='inner')",
        "df_times = pd.merge(df_times, order_reviews[['order_id', 'review_score']], on='order_id', how='left')",
        "df_times = pd.merge(df_times, customers[['customer_id', 'customer_state']], on='customer_id', how='left')",
        "",
        "# 3. Calculamos las diferencias de tiempos en Días (Valores POSITIVOS = Llegó antes de la fecha límite/estimada)",
        "# Diferencia entre Límite del Seller y Llegada Real al Carrier",
        "df_times['diff_limit_carrier'] = (df_times['shipping_limit_date'] - df_times['order_delivered_carrier_date']).dt.total_seconds() / (24*3600)",
        "",
        "# Diferencia entre Estimación del Cliente y Llegada Real al Cliente",
        "df_times['diff_estimated_customer'] = (df_times['order_estimated_delivery_date'] - df_times['order_delivered_customer_date']).dt.total_seconds() / (24*3600)"
    ]
    
    code_2 = [
        "# Gráfico 1.1: Diff Carrier por Estado",
        "plt.figure(figsize=(15, 4))",
        "avg_lim_carrier_state = df_times.groupby('customer_state')['diff_limit_carrier'].mean().sort_values(ascending=False).reset_index()",
        "sns.barplot(data=avg_lim_carrier_state, x='customer_state', y='diff_limit_carrier', hue='customer_state', palette='viridis', legend=False)",
        "plt.title('Diferencia de días: [Límite de Envío] vs [Entrega al Carrier] por Estado\\n(Positivo = El seller lo entregó a tiempo al centro logístico)')",
        "plt.ylabel('Días Promedio')",
        "plt.axhline(0, color='red', linestyle='--')",
        "plt.show()"
    ]
    
    code_3 = [
        "# Gráfico 1.2: Diff Carrier por Review",
        "plt.figure(figsize=(8, 4))",
        "avg_lim_carrier_review = df_times.groupby('review_score')['diff_limit_carrier'].mean().reset_index()",
        "sns.barplot(data=avg_lim_carrier_review, x='review_score', y='diff_limit_carrier', hue='review_score', palette='coolwarm', legend=False)",
        "plt.title('Diferencia de días: [Límite de Envío] vs [Entrega al Carrier] agrupado por Review')",
        "plt.ylabel('Días Promedio')",
        "plt.xlabel('Review Score')",
        "plt.axhline(0, color='red', linestyle='--')",
        "plt.show()"
    ]
    
    code_4 = [
        "# Gráfico 2.1: Diff Estimado vs Cliente por Estado",
        "plt.figure(figsize=(15, 4))",
        "avg_est_customer_state = df_times.groupby('customer_state')['diff_estimated_customer'].mean().sort_values(ascending=False).reset_index()",
        "sns.barplot(data=avg_est_customer_state, x='customer_state', y='diff_estimated_customer', hue='customer_state', palette='viridis', legend=False)",
        "plt.title('Diferencia de días: [Llegada Estimada] vs [Llegada Real al Cliente] por Estado\\n(Positivo = Llegó al cliente antes de lo esperado)')",
        "plt.ylabel('Días Promedio')",
        "plt.axhline(0, color='red', linestyle='--')",
        "plt.show()"
    ]
    
    code_5 = [
        "# Gráfico 2.2: Diff Estimado vs Cliente por Review",
        "plt.figure(figsize=(8, 4))",
        "avg_est_customer_review = df_times.groupby('review_score')['diff_estimated_customer'].mean().reset_index()",
        "sns.barplot(data=avg_est_customer_review, x='review_score', y='diff_estimated_customer', hue='review_score', palette='coolwarm', legend=False)",
        "plt.title('Diferencia de días: [Llegada Estimada] vs [Llegada Real al Cliente] agrupado por Review')",
        "plt.ylabel('Días Promedio')",
        "plt.xlabel('Review Score')",
        "plt.axhline(0, color='red', linestyle='--')",
        "plt.show()"
    ]
    
    code_6 = [
        "# Proporción General: Cuántos llegaron al carrier ANTES del límite de envío",
        "llegaron_ok_carrier = (df_times['diff_limit_carrier'] > 0).sum()",
        "total_valid_carrier = df_times['diff_limit_carrier'].notna().sum()",
        "prop_carrier = llegaron_ok_carrier / total_valid_carrier if total_valid_carrier > 0 else 0",
        "print(f\"➜ Del total de órdenes completadas, en el {prop_carrier:.2%} de los casos el seller envió el paquete al carrier ANTES del tiempo límite.\\n\")"
    ]
    
    code_7 = [
        "# Para el último gráfico, filtramos SOLO los casos donde el paquete SI llegó \"a tiempo\" al Carrier:",
        "df_a_tiempo = df_times[df_times['diff_limit_carrier'] > 0].copy()",
        "",
        "# Calculamos cuándo order_estimated_delivery_date fue Menor que order_delivered_carrier_date",
        "# Ojo: estamos comparando el Estimado al Cliente vs Entregado al Carrier (tal cual lo pediste)",
        "cond_menor = (df_a_tiempo['order_estimated_delivery_date'] < df_a_tiempo['order_delivered_carrier_date']).sum()",
        "cond_mayor = (df_a_tiempo['order_estimated_delivery_date'] >= df_a_tiempo['order_delivered_carrier_date']).sum()",
        "",
        "labels = ['Estimado < Llegó a Carrier', 'Estimado >= Llegó a Carrier']",
        "sizes = [cond_menor, cond_mayor]",
        "",
        "plt.figure(figsize=(6, 6))",
        "plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=140, colors=['salmon', 'lightgreen'])",
        "plt.title('Proporción: [Fecha Estimada] vs [Fecha Entregado al Carrier]\\n(Sólo en órdenes despachadas a tiempo por el Seller)')",
        "plt.show()"
    ]
    
    new_cells = [
        m("### 10.1. Preparación de datos de tiempos y logística"),
        c(code_1),
        m("### 10.2. Límite de Envío vs Entrega al Carrier por Estado"),
        c(code_2),
        m("### 10.3. Límite de Envío vs Entrega al Carrier por Review"),
        c(code_3),
        m("### 10.4. Llegada Estimada vs Llegada Real al Cliente por Estado"),
        c(code_4),
        m("### 10.5. Llegada Estimada vs Llegada Real al Cliente por Review"),
        c(code_5),
        m("### 10.6. Proporción General de cumplimiento en envío al carrier"),
        c(code_6),
        m("### 10.7. Proporción Fecha Estimada vs Fecha Entregado al Carrier (órdenes a tiempo)"),
        c(code_7)
    ]
    
    # Check if there is already these individual cells in the notebook to avoid duplicates
    nb['cells'] = nb['cells'][:target_idx] + new_cells + nb['cells'][target_idx+1:]
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(nb, f, indent=1, ensure_ascii=False)
        
    print("Notebook modified successfully.")
else:
    print("Target cell not found.")
