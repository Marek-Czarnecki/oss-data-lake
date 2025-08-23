from airflow import DAG
from airflow.operators.empty import EmptyOperator
from datetime import datetime

with DAG(
    dag_id="sanity_ok",
    start_date=datetime(2025, 8, 1),
    schedule_interval=None,
    catchup=False,
    tags=["sanity"],
):
    EmptyOperator(task_id="it_runs")

