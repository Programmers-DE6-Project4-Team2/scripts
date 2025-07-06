import os
import json
import logging
from datetime import datetime
from google.cloud import storage
from dotenv import load_dotenv
import pandas as pd

# 로컬 환경일 경우 dotenv 로드
if os.environ.get("ENV", "").lower() != "production":
    load_dotenv()

def upload_json_to_gcs(bucket_name: str, data: dict, destination_blob_name: str):
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_string(
        data=json.dumps(data, ensure_ascii=False, indent=2),
        content_type="application/json"
    )
    logging.info(f"✅ Uploaded JSON to gs://{bucket_name}/{destination_blob_name}")

def upload_csv_to_gcs(bucket_name: str, dataframe: pd.DataFrame, destination_blob_name: str):
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_string(
        dataframe.to_csv(index=False, encoding='utf-8-sig'),
        content_type="text/csv"
    )
    logging.info(f"✅ Uploaded CSV to gs://{bucket_name}/{destination_blob_name}")
