from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
import requests
from categories import get_all_categories

def trigger_product_api(category_name, category_id):
    url = "https://YOUR_CLOUD_RUN_URL/run/product"  # <- 실제 배포된 Cloud Run URL로 변경 필요
    payload = {
        "category_name": category_name,
        "category_id": category_id,
        "max_pages": 25,
        "bucket_name": "your-gcs-bucket"  # <- 실제 GCS 버킷명으로 변경
    }
    response = requests.post(url, json=payload)
    print(f"[{category_name}] status: {response.status_code}")
    print(response.text)

with DAG(
    dag_id="naver_product_collect_dag",
    start_date=datetime(2025, 7, 7),
    schedule_interval="@daily",
    catchup=False,
    tags=["naver", "product", "cloudrun"]
) as dag:

    categories = get_all_categories()

    for category_name, category_id in categories.items():
        PythonOperator(
            task_id=f"collect_{category_name.replace('/', '_')}",
            python_callable=trigger_product_api,
            op_args=[category_name, category_id]
        )
