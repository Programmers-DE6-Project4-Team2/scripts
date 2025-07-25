#!/usr/bin/env python3
"""
Google Cloud Storage 업로드 유틸리티 (Airflow 병렬 처리용)
무신사 크롤러 전용 GCS 업로드 함수들
"""

import json
import logging
import pandas as pd
from google.cloud import storage
from typing import Any, Optional
import io

# 로깅 설정
logger = logging.getLogger(__name__)


def upload_csv_to_gcs(bucket_name: str, dataframe: pd.DataFrame,
                      destination_blob_name: str, project_id: Optional[str] = None) -> bool:
    """DataFrame을 CSV로 GCS에 업로드"""
    try:
        # GCS 클라이언트 생성
        if project_id:
            client = storage.Client(project=project_id)
        else:
            client = storage.Client()

        # 버킷과 blob 객체 생성
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(destination_blob_name)

        # DataFrame을 CSV 문자열로 변환
        csv_buffer = io.StringIO()
        dataframe.to_csv(csv_buffer, index=False, encoding='utf-8')
        csv_string = csv_buffer.getvalue()

        # GCS에 업로드
        blob.upload_from_string(csv_string, content_type='text/csv')

        logger.info(f"CSV 파일 GCS 업로드 완료: {destination_blob_name}")
        return True

    except Exception as e:
        logger.error(f"CSV 파일 GCS 업로드 실패: {destination_blob_name}, 오류: {str(e)}")
        return False


def upload_json_to_gcs(bucket_name: str, data: Any, destination_blob_name: str,
                       project_id: Optional[str] = None) -> bool:
    """JSON 데이터를 GCS에 업로드"""
    try:
        # GCS 클라이언트 생성
        if project_id:
            client = storage.Client(project=project_id)
        else:
            client = storage.Client()

        # 버킷과 blob 객체 생성
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(destination_blob_name)

        # 데이터를 JSON 문자열로 변환
        json_string = json.dumps(data, ensure_ascii=False, indent=2)

        # GCS에 업로드
        blob.upload_from_string(json_string, content_type='application/json')

        logger.info(f"JSON 파일 GCS 업로드 완료: {destination_blob_name}")
        return True

    except Exception as e:
        logger.error(f"JSON 파일 GCS 업로드 실패: {destination_blob_name}, 오류: {str(e)}")
        return False


def upload_file_to_gcs(bucket_name: str, source_file_name: str,
                       destination_blob_name: str, project_id: Optional[str] = None) -> bool:
    """로컬 파일을 GCS에 업로드"""
    try:
        # GCS 클라이언트 생성
        if project_id:
            client = storage.Client(project=project_id)
        else:
            client = storage.Client()

        # 버킷과 blob 객체 생성
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(destination_blob_name)

        # 파일 업로드
        blob.upload_from_filename(source_file_name)

        logger.info(f"파일 GCS 업로드 완료: {source_file_name} -> {destination_blob_name}")
        return True

    except Exception as e:
        logger.error(f"파일 GCS 업로드 실패: {source_file_name}, 오류: {str(e)}")
        return False


def check_blob_exists(bucket_name: str, blob_name: str, project_id: Optional[str] = None) -> bool:
    """GCS에 파일이 존재하는지 확인"""
    try:
        # GCS 클라이언트 생성
        if project_id:
            client = storage.Client(project=project_id)
        else:
            client = storage.Client()

        # 버킷과 blob 객체 생성
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_name)

        # 파일 존재 여부 확인
        exists = blob.exists()

        logger.info(f"파일 존재 여부 확인: {blob_name} -> {'존재' if exists else '없음'}")
        return exists

    except Exception as e:
        logger.error(f"파일 존재 여부 확인 실패: {blob_name}, 오류: {str(e)}")
        return False


def delete_blob_from_gcs(bucket_name: str, blob_name: str, project_id: Optional[str] = None) -> bool:
    """GCS에서 파일 삭제"""
    try:
        # GCS 클라이언트 생성
        if project_id:
            client = storage.Client(project=project_id)
        else:
            client = storage.Client()

        # 버킷과 blob 객체 생성
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_name)

        # 파일 삭제
        blob.delete()

        logger.info(f"파일 GCS 삭제 완료: {blob_name}")
        return True

    except Exception as e:
        logger.error(f"파일 GCS 삭제 실패: {blob_name}, 오류: {str(e)}")
        return False
