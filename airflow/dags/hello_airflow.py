from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime

def saludo():
    print("Hola desde Airflow 🚀")

with DAG(
    dag_id="hello_airflow",
    start_date=datetime(2025, 1, 1),
    schedule="@daily",
    catchup=False
) as dag:

    task = PythonOperator(
        task_id="saludar",
        python_callable=saludo
    )