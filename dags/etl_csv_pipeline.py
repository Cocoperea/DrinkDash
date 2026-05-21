import os
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# RUTAS
if os.name == 'nt':  
    INPUT_DIR = "data/input_csv"
    DB_PATH = "data/drinkdash.db"
else:
    INPUT_DIR = "/opt/airflow/data/input_csv"
    DB_PATH = "/opt/airflow/data/drinkdash.db"

def _procesar_csv_a_sqlite():
    print(f"Buscando archivos en: {INPUT_DIR}")
    
    # Creamos la carpeta automáticamente si no existe para evitar errores
    if not os.path.exists(INPUT_DIR):
        os.makedirs(INPUT_DIR)
        print("Carpeta creada. Por favor, pegá el archivo 'sales_drinks.csv' adentro y volvé a correr el script.")
        return

    archivos = [f for f in os.listdir(INPUT_DIR) if f.endswith('.csv') and not f.startswith('procesado_')]
    
    if not archivos:
        print("No se detectaron archivos CSV nuevos en la carpeta de entrada.")
        return
        
    for archivo in archivos:
        ruta_completa = os.path.join(INPUT_DIR, archivo)
        print(f"Procesando archivo: {archivo}")
        df = pd.read_csv(ruta_completa) #Convierto el archivo en un dataframe

        # EXTRACT & TRANSFORM
         
        # 1. Eliminación de nulos usando el nombre real de la columna
        df = df.dropna(subset=['invoice_id', 'purchase_datetime', 'amount', 'sku']) #Borro cualquier fila que tenga datos vacíos en esas columnas
        
        # 2. Eliminación de duplicados
        df = df.drop_duplicates(subset=['invoice_id', 'sku']) 
        
        # 3. Validación de cantidades y precios mayores a cero
        df = df[(df['quantity'] > 0) & (df['unit_price'] > 0)] 
        
        # 4. Validación de consistencia del monto final
        monto_calculado = df['unit_price'] * df['quantity'] * (1 - df['discount_pct'])
        df = df[np.isclose(df['amount'], monto_calculado, atol=0.01)] #verifico que el monto cobrado sea casi igual al calculado con np.isclose
        
        # 5. Enriquecimiento para los dashboards
        df['purchase_datetime'] = pd.to_datetime(df['purchase_datetime'])
        df['purchase_hour'] = df['purchase_datetime'].dt.hour #creo columna y guardo la hora
        df['revenue_bruto'] = df['unit_price'] * df['quantity'] #calculo el revenue bruto 
        df['revenue_sacrificado'] = df['revenue_bruto'] - df['amount'] #calculo el revenue sacrificado
        
        # LOAD
        #abro la conexion e inserto la tabla, si ya existe solo agrega las nuevas ventas
        conn = sqlite3.connect(DB_PATH)
        df.to_sql('ventas_procesadas', conn, if_exists='append', index=False)
        conn.close()
        
        #renombro para no volver a procesar
        ruta_procesado = os.path.join(INPUT_DIR, f"procesado_{archivo}")
        os.rename(ruta_completa, ruta_procesado)
        print(f"Archivo cargado en la base de datos: {DB_PATH}")

# BLOQUE AIRFLOW
try:
    from airflow import DAG
    from airflow.operators.python import PythonOperator

    default_args = {"owner": "Grupo_10", "retries": 1, "retry_delay": timedelta(minutes=1)}
    
    with DAG(
        dag_id="drinkdash_csv_etl",
        start_date=datetime(2026, 5, 1),
        schedule_interval="*/5 * * * *", 
        catchup=False,
        tags=["drinkdash", "grupo10"]
    ) as dag:
        procesar_datos = PythonOperator(
            task_id="extraer_transformar_cargar_csv",
            python_callable=_procesar_csv_a_sqlite,
        )
except ImportError:
    #Si Airflow no está instalado simplemente sigue de largo
    pass

# BLOQUE PARA PRUEBA LOCAL
if __name__ == "__main__":
    _procesar_csv_a_sqlite()