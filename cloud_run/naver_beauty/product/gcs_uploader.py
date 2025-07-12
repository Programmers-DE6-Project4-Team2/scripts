# gcs_uploader.py
from google.cloud import storage
from typing import Union

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
