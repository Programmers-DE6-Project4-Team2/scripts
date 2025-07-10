# gcs_uploader.py
from google.cloud import storage
from typing import Union
import logging

def upload_to_gcs(bucket_name: str, content: Union[str, bytes], blob_path: str,
                  content_type: str = "application/octet-stream", from_bytes: bool = False):
    """GCS에 파일 업로드 - 로컬 경로 or 바이너리 데이터"""
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_path)

    if from_bytes:
        # bytes 객체 그대로 업로드
        blob.upload_from_string(content, content_type=content_type)
    else:
        # 파일 경로에서 업로드
        with open(content, "rb") as f:
            blob.upload_from_file(f, content_type=content_type)
    
    #logging.info(f"✅ 업로드 완료: gs://{bucket_name}/{blob_path}")


def find_latest_product_csv_blob(bucket_name: str, category_name: str):
    """
    GCS에서 raw-data/naver/{category_name}/{timestamp}/{category_name}_{timestamp}.csv 중 최신 파일 blob 반환
    """
    from google.cloud import storage

    client = storage.Client()
    bucket = client.bucket(bucket_name)

    # ✅ 정확히 상품 목록만 찾도록 prefix 제한
    prefix = f"raw-data/naver/{category_name}/"

    blobs = list(bucket.list_blobs(prefix=prefix))
    csv_blobs = [
        blob for blob in blobs
        if blob.name.endswith(".csv")
        and "/reviews/" not in blob.name  # ✅ 리뷰 디렉토리는 제외
    ]

    if not csv_blobs:
        raise FileNotFoundError(f"❌ GCS에 상품 CSV 파일이 없습니다: gs://{bucket_name}/{prefix}")

    latest_blob = max(csv_blobs, key=lambda b: b.updated)
    return latest_blob
