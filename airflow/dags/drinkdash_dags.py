import sys
from pathlib import Path
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

from dashboard.etl.etl_csv_pipeline import procesar_csv_a_sqlite


sys.path.append(str(Path(__file__).resolve().parents[2]))

default_args = {
    "owner": "Grupo_10",
    "retries": 1,
    "retry_delay": timedelta(minutes=1),
}

with DAG(
    dag_id="drinkdash_etl",
    default_args=default_args,
    start_date=datetime(2026, 5, 1),
    schedule="*/5 * * * *",
    catchup=False,
    tags=["drinkdash"],
) as dag:

    run_etl = PythonOperator(
        task_id="procesar_csv",
        python_callable=procesar_csv_a_sqlite,
    )