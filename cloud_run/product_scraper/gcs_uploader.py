"""
Google Cloud Storage 업로더
크롤링된 데이터를 GCS에 업로드하는 유틸리티
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, List
from google.cloud import storage

logger = logging.getLogger(__name__)

class GCSUploader:
    def __init__(self):
        self.project_id = os.environ.get('PROJECT_ID')
        self.bucket_name = os.environ.get('GCS_BUCKET')
        
        if not self.project_id or not self.bucket_name:
            raise ValueError("PROJECT_ID and GCS_BUCKET environment variables are required")
        
        self.client = storage.Client(project=self.project_id)
        self.bucket = self.client.bucket(self.bucket_name)
        
        logger.info(f"GCS Uploader initialized - Project: {self.project_id}, Bucket: {self.bucket_name}")
    
    def upload_json(self, data: Dict[str, Any], file_path: str) -> Dict[str, str]:
        """JSON 데이터를 GCS에 업로드"""
        try:
            # JSON 문자열로 변환
            json_data = json.dumps(data, ensure_ascii=False, indent=2)
            
            # GCS에 업로드
            blob = self.bucket.blob(file_path)
            blob.upload_from_string(
                json_data,
                content_type='application/json'
            )
            
            # 메타데이터 설정
            blob.metadata = {
                'uploaded_at': datetime.now().isoformat(),
                'data_type': data.get('metadata', {}).get('data_type', 'unknown'),
                'source': data.get('metadata', {}).get('source', 'unknown'),
                'records_count': str(len(data.get('products', [])))
            }
            blob.patch()
            
            gcs_path = f"gs://{self.bucket_name}/{file_path}"
            logger.info(f"Successfully uploaded data to {gcs_path}")
            
            return {
                'status': 'success',
                'gcs_path': gcs_path,
                'file_size': len(json_data),
                'uploaded_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error uploading to GCS: {str(e)}")
            raise
    
    def upload_csv(self, data: List[Dict], file_path: str) -> Dict[str, str]:
        """CSV 데이터를 GCS에 업로드"""
        try:
            import pandas as pd
            
            # DataFrame으로 변환
            df = pd.DataFrame(data)
            
            # CSV 문자열로 변환
            csv_data = df.to_csv(index=False, encoding='utf-8')
            
            # GCS에 업로드
            blob = self.bucket.blob(file_path)
            blob.upload_from_string(
                csv_data,
                content_type='text/csv'
            )
            
            # 메타데이터 설정
            blob.metadata = {
                'uploaded_at': datetime.now().isoformat(),
                'records_count': str(len(data)),
                'columns': ','.join(df.columns.tolist())
            }
            blob.patch()
            
            gcs_path = f"gs://{self.bucket_name}/{file_path}"
            logger.info(f"Successfully uploaded CSV to {gcs_path}")
            
            return {
                'status': 'success',
                'gcs_path': gcs_path,
                'file_size': len(csv_data),
                'uploaded_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error uploading CSV to GCS: {str(e)}")
            raise
    
    def list_files(self, prefix: str) -> List[str]:
        """특정 prefix로 시작하는 파일 목록 반환"""
        try:
            blobs = self.client.list_blobs(self.bucket, prefix=prefix)
            return [blob.name for blob in blobs]
        except Exception as e:
            logger.error(f"Error listing files: {str(e)}")
            return []
    
    def download_json(self, file_path: str) -> Dict[str, Any]:
        """GCS에서 JSON 파일 다운로드"""
        try:
            blob = self.bucket.blob(file_path)
            json_data = blob.download_as_text()
            return json.loads(json_data)
        except Exception as e:
            logger.error(f"Error downloading from GCS: {str(e)}")
            raise
    
    def file_exists(self, file_path: str) -> bool:
        """파일 존재 여부 확인"""
        try:
            blob = self.bucket.blob(file_path)
            return blob.exists()
        except Exception as e:
            logger.error(f"Error checking file existence: {str(e)}")
            return False