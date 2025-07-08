#!/usr/bin/env python3
"""
Google Cloud Storage 업로드 유틸리티
팀원 코드와 동일한 구조로 작성
"""

import os
import json
import logging
import pandas as pd
from google.cloud import storage
from typing import Any, Dict, List, Optional
from datetime import datetime
import io

logger = logging.getLogger(__name__)


class GCSUploader:
    """Google Cloud Storage 업로드 클래스"""

    def __init__(self, bucket_name: str, project_id: Optional[str] = None):
        """
        GCS 업로더 초기화

        Args:
            bucket_name: GCS 버킷 이름
            project_id: GCP 프로젝트 ID (선택사항)
        """
        self.bucket_name = bucket_name
        self.project_id = project_id
        self.client = None
        self.bucket = None
        self._initialize_client()

    def _initialize_client(self):
        """GCS 클라이언트 초기화"""
        try:
            if self.project_id:
                self.client = storage.Client(project=self.project_id)
            else:
                self.client = storage.Client()

            self.bucket = self.client.bucket(self.bucket_name)
            logger.info(f"GCS 클라이언트 초기화 완료: {self.bucket_name}")

        except Exception as e:
            logger.error(f"GCS 클라이언트 초기화 실패: {e}")
            raise


def upload_csv_to_gcs(bucket_name: str, dataframe: pd.DataFrame,
                      destination_blob_name: str, project_id: Optional[str] = None) -> bool:
    """DataFrame을 CSV로 GCS에 업로드"""
    try:
        # GCS 클라이언트 초기화
        if project_id:
            client = storage.Client(project=project_id)
        else:
            client = storage.Client()

        bucket = client.bucket(bucket_name)
        blob = bucket.blob(destination_blob_name)

        # DataFrame을 CSV 문자열로 변환
        csv_buffer = io.StringIO()
        dataframe.to_csv(csv_buffer, index=False, encoding='utf-8')
        csv_string = csv_buffer.getvalue()

        # GCS에 업로드
        blob.upload_from_string(csv_string, content_type='text/csv')

        logger.info(f"CSV 파일이 GCS에 업로드되었습니다: gs://{bucket_name}/{destination_blob_name}")
        return True

    except Exception as e:
        logger.error(f"CSV GCS 업로드 실패: {e}")
        return False


def upload_json_to_gcs(bucket_name: str, data: Any,
                       destination_blob_name: str, project_id: Optional[str] = None) -> bool:
    """JSON 데이터를 GCS에 업로드"""
    try:
        # GCS 클라이언트 초기화
        if project_id:
            client = storage.Client(project=project_id)
        else:
            client = storage.Client()

        bucket = client.bucket(bucket_name)
        blob = bucket.blob(destination_blob_name)

        # JSON 문자열로 변환
        json_string = json.dumps(data, ensure_ascii=False, indent=2)

        # GCS에 업로드
        blob.upload_from_string(json_string, content_type='application/json')

        logger.info(f"JSON 파일이 GCS에 업로드되었습니다: gs://{bucket_name}/{destination_blob_name}")
        return True

    except Exception as e:
        logger.error(f"JSON GCS 업로드 실패: {e}")
        return False


def upload_file_to_gcs(bucket_name: str, source_file_name: str,
                       destination_blob_name: str, project_id: Optional[str] = None) -> bool:
    """로컬 파일을 GCS에 업로드"""
    try:
        # GCS 클라이언트 초기화
        if project_id:
            client = storage.Client(project=project_id)
        else:
            client = storage.Client()

        bucket = client.bucket(bucket_name)
        blob = bucket.blob(destination_blob_name)

        # 파일 업로드
        blob.upload_from_filename(source_file_name)

        logger.info(f"파일이 GCS에 업로드되었습니다: gs://{bucket_name}/{destination_blob_name}")
        return True

    except Exception as e:
        logger.error(f"파일 GCS 업로드 실패: {e}")
        return False


def list_gcs_files(bucket_name: str, prefix: str = "", project_id: Optional[str] = None) -> List[str]:
    """GCS 버킷의 파일 목록 조회"""
    try:
        if project_id:
            client = storage.Client(project=project_id)
        else:
            client = storage.Client()

        bucket = client.bucket(bucket_name)
        blobs = bucket.list_blobs(prefix=prefix)

        file_list = [blob.name for blob in blobs]
        logger.info(f"GCS 파일 목록 조회 완료: {len(file_list)}개 파일")
        return file_list

    except Exception as e:
        logger.error(f"GCS 파일 목록 조회 실패: {e}")
        return []


def download_from_gcs(bucket_name: str, source_blob_name: str,
                      destination_file_name: str, project_id: Optional[str] = None) -> bool:
    """GCS에서 파일 다운로드"""
    try:
        if project_id:
            client = storage.Client(project=project_id)
        else:
            client = storage.Client()

        bucket = client.bucket(bucket_name)
        blob = bucket.blob(source_blob_name)

        blob.download_to_filename(destination_file_name)

        logger.info(f"GCS에서 파일 다운로드 완료: {destination_file_name}")
        return True

    except Exception as e:
        logger.error(f"GCS 파일 다운로드 실패: {e}")
        return False


def check_gcs_connection(bucket_name: str, project_id: Optional[str] = None) -> bool:
    """GCS 연결 상태 확인"""
    try:
        if project_id:
            client = storage.Client(project=project_id)
        else:
            client = storage.Client()

        bucket = client.bucket(bucket_name)

        # 버킷 존재 여부 확인
        if bucket.exists():
            logger.info(f"GCS 버킷 연결 성공: {bucket_name}")
            return True
        else:
            logger.error(f"GCS 버킷이 존재하지 않습니다: {bucket_name}")
            return False

    except Exception as e:
        logger.error(f"GCS 연결 확인 실패: {e}")
        return False


def get_gcs_file_info(bucket_name: str, blob_name: str, project_id: Optional[str] = None) -> Optional[Dict]:
    """GCS 파일 정보 조회"""
    try:
        if project_id:
            client = storage.Client(project=project_id)
        else:
            client = storage.Client()

        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_name)

        if blob.exists():
            return {
                "name": blob.name,
                "size": blob.size,
                "created": blob.time_created.isoformat() if blob.time_created else None,
                "updated": blob.updated.isoformat() if blob.updated else None,
                "content_type": blob.content_type,
                "md5_hash": blob.md5_hash,
                "public_url": blob.public_url
            }
        else:
            logger.warning(f"GCS 파일이 존재하지 않습니다: {blob_name}")
            return None

    except Exception as e:
        logger.error(f"GCS 파일 정보 조회 실패: {e}")
        return None
