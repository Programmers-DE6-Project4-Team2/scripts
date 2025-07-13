#!/usr/bin/env python3

"""
무신사 데이터 수집 Cloud Run Job 애플리케이션 (GCS 연동 포함)
Docker 환경에서 실행되는 크롤링 서비스
"""
import json
import os
import logging
from datetime import datetime
from dotenv import load_dotenv
import pandas as pd

# 로컬 환경일 경우 dotenv 로드
if os.environ.get("ENV", "").lower() != "production":
    load_dotenv()

from musinsa_crawler import MusinsaCrawler
from utils import CATEGORY_MAPPING
from gcs_uploader import (
    upload_csv_to_gcs,
    upload_json_to_gcs,
    upload_file_to_gcs
)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


class MusinsaDataPipeline:
    """무신사 데이터 수집 파이프라인 (카테고리별 GCS 연동 포함)"""

    def __init__(self):
        self.bucket_name = os.environ.get("GCS_BUCKET_NAME")
        self.project_id = os.environ.get("GCS_PROJECT_ID")
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.date_str = datetime.now().strftime("%Y%m%d")
        self.gcs_enabled = bool(self.bucket_name and self.bucket_name != "your-bucket-name")

        if self.gcs_enabled:
            logger.info(f"GCS 업로드 활성화: {self.bucket_name}")
        else:
            logger.info("GCS 업로드 비활성화 - 로컬 저장만 수행")

    def get_category_folder_name(self, category_code: str) -> str:
        """카테고리 코드를 폴더명으로 변환 (슬래시를 &로 변경)"""
        category_name = CATEGORY_MAPPING.get(category_code, f"category_{category_code}")
        return category_name.replace("/", "&")

    def _upload_to_gcs_with_category(self, data: any, filename: str, file_type: str,
                                     category_code: str, data_type: str) -> bool:
        """카테고리별 GCS 업로드 헬퍼 메서드"""
        if not self.gcs_enabled:
            return False
        try:
            category_folder = self.get_category_folder_name(category_code)
            # 새로운 경로 구조: musinsa/{data_type}/{category_folder}/{date}/
            gcs_path = f"raw-data/musinsa/{data_type}/{category_folder}/{self.date_str}/{filename}"

            if file_type == "csv" and isinstance(data, pd.DataFrame):
                return upload_csv_to_gcs(self.bucket_name, data, gcs_path, self.project_id)
            elif file_type == "json":
                return upload_json_to_gcs(self.bucket_name, data, gcs_path, self.project_id)
            elif file_type == "file":
                return upload_file_to_gcs(self.bucket_name, data, gcs_path, self.project_id)
            else:
                logger.error(f"지원하지 않는 파일 타입: {file_type}")
                return False
        except Exception as e:
            logger.error(f"GCS 업로드 중 오류: {e}")
            return False

    def _upload_to_gcs(self, data: any, filename: str, file_type: str, folder: str = "",
                       category_code: str = None) -> bool:
        """GCS 업로드 헬퍼 메서드 (카테고리별 폴더 구조 지원)"""
        if not self.gcs_enabled:
            return False
        try:
            if category_code:
                # 카테고리별 폴더 구조 생성
                category_folder = self.get_category_folder_name(category_code)
                gcs_path = f"raw-data/musinsa/{folder}/{category_folder}/{self.date_str}/{filename}"
            elif folder:
                gcs_path = f"raw-data/musinsa/{folder}/{filename}"
            else:
                gcs_path = f"raw-data/musinsa/{filename}"

            if file_type == "csv" and isinstance(data, pd.DataFrame):
                return upload_csv_to_gcs(self.bucket_name, data, gcs_path, self.project_id)
            elif file_type == "json":
                return upload_json_to_gcs(self.bucket_name, data, gcs_path, self.project_id)
            elif file_type == "file":
                return upload_file_to_gcs(self.bucket_name, data, gcs_path, self.project_id)
            else:
                logger.error(f"지원하지 않는 파일 타입: {file_type}")
                return False
        except Exception as e:
            logger.error(f"GCS 업로드 중 오류: {e}")
            return False

    def run_single_category_ranking(self, category_code: str) -> dict:
        """단일 카테고리 랭킹 수집"""
        try:
            logger.info(f"카테고리 {category_code} 랭킹 수집 시작")

            crawler = MusinsaCrawler(
                section_id="231",
                size=40,
                max_pages=int(os.environ.get("MAX_PAGES", "8")),
                review_page_size=20,
                review_max_pages=1  # 랭킹만 수집
            )

            result = crawler.crawl_single_category_ranking(category_code)

            # GCS 업로드
            if self.gcs_enabled and result['products']:
                success = self._upload_ranking_to_gcs(result, category_code)
                result['gcs_uploaded'] = success

            logger.info(f"카테고리 {category_code} 랭킹 수집 완료 - {result['product_count']}개 상품")

            # product_ids 반환 (다음 단계에서 사용)
            product_ids = [p['product_id'] for p in result['products'] if p.get('product_id')]

            return {
                "status": "success",
                "message": f"카테고리 {category_code} 랭킹 수집 완료",
                "data": {
                    "category_code": category_code,
                    "product_ids": product_ids,
                    "product_count": len(product_ids),
                    "created_at": result['created_at']
                }
            }

        except Exception as e:
            logger.error(f"카테고리 {category_code} 랭킹 수집 중 오류: {e}")
            return {"status": "error", "message": str(e)}

    def _upload_reviews_to_gcs(self, result: dict) -> bool:
        """리뷰 데이터 GCS 업로드"""
        try:
            category_code = result['category_code']
            batch_index = result['batch_index']
            category_folder = self.get_category_folder_name(category_code)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            csv_filename = f"review_{category_folder}_{category_code}_batch_{batch_index}_{timestamp}.csv"

            # 리뷰 데이터를 플랫 구조로 변환
            from musinsa_review_collector import MusinsaReviewCollector
            temp_collector = MusinsaReviewCollector(None, [])
            review_rows = temp_collector.flatten_reviews(result['reviews'])

            df = pd.DataFrame(review_rows)

            return self._upload_to_gcs(
                df, csv_filename, "csv", "reviews", category_code
            )

        except Exception as e:
            logger.error(f"리뷰 데이터 GCS 업로드 실패: {e}")
            return False

    def run_review_batch(self, product_ids_str: str, batch_info_str: str) -> dict:
        """배치별 리뷰 수집"""
        try:
            import json

            # JSON 문자열을 파이썬 객체로 변환
            product_ids = json.loads(product_ids_str) if isinstance(product_ids_str, str) else product_ids_str
            batch_info = json.loads(batch_info_str) if isinstance(batch_info_str, str) else batch_info_str

            logger.info(f"배치 {batch_info.get('batch_index', 0)} 리뷰 수집 시작 - {len(product_ids)}개 상품")

            crawler = MusinsaCrawler(
                section_id="231",
                size=40,
                max_pages=1,  # 리뷰만 수집
                review_page_size=20,
                review_max_pages=int(os.environ.get("REVIEW_PAGES", "25"))
            )

            result = crawler.crawl_review_batch(product_ids, batch_info)

            # GCS 업로드
            if self.gcs_enabled and result['reviews']:
                success = self._upload_reviews_to_gcs(result)
                result['gcs_uploaded'] = success

            logger.info(f"배치 {result['batch_index']} 리뷰 수집 완료 - {result['review_count']}개 리뷰")

            return {
                "status": "success",
                "message": f"배치 {result['batch_index']} 리뷰 수집 완료",
                "data": result
            }

        except Exception as e:
            logger.error(f"배치 리뷰 수집 중 오류: {e}")
            return {"status": "error", "message": str(e)}

    def create_review_batches_from_ids(self, product_ids_str: str, category_code: str, batch_size: int = 30) -> dict:
        """product_ids를 배치로 나누기"""
        try:
            import json

            product_ids = json.loads(product_ids_str) if isinstance(product_ids_str, str) else product_ids_str

            batches = MusinsaCrawler.create_review_batches(product_ids, batch_size)

            # 각 배치에 category_code 추가
            for batch in batches:
                batch['category_code'] = category_code

            return {
                "status": "success",
                "message": f"{len(product_ids)}개 상품을 {len(batches)}개 배치로 분할",
                "data": {
                    "category_code": category_code,
                    "total_products": len(product_ids),
                    "batch_count": len(batches),
                    "batch_size": batch_size,
                    "batches": batches
                }
            }

        except Exception as e:
            logger.error(f"배치 생성 중 오류: {e}")
            return {"status": "error", "message": str(e)}

    def _upload_ranking_to_gcs(self, result: dict, category_code: str) -> bool:
        """랭킹 데이터 GCS 업로드"""
        try:
            category_folder = self.get_category_folder_name(category_code)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            csv_filename = f"product_{category_folder}_{category_code}_{timestamp}.csv"

            df = pd.DataFrame(result['products'])

            return self._upload_to_gcs(
                df, csv_filename, "csv", "products", category_code
            )

        except Exception as e:
            logger.error(f"랭킹 데이터 GCS 업로드 실패: {e}")
            return False


def main():
    """메인 함수 - 환경변수에 따른 실행 모드 결정"""
    logger.info("무신사 데이터 크롤링 서비스 시작")

    pipeline = MusinsaDataPipeline()

    # 환경변수로 실행 모드 결정
    mode = os.environ.get("CRAWL_MODE", "all-categories").lower()

    # 새로운 환경변수들
    category_code = os.environ.get("CATEGORY_CODE", "")
    product_ids = os.environ.get("PRODUCT_IDS", "")
    batch_info = os.environ.get("BATCH_INFO", "")
    batch_size = int(os.environ.get("BATCH_SIZE", "30"))

    logger.info(f"실행 모드: {mode}")

    if mode == "single-category-ranking":
        # 단일 카테고리 랭킹 수집
        if not category_code:
            logger.error("CATEGORY_CODE 환경변수가 필요합니다.")
            exit(1)
        result = pipeline.run_single_category_ranking(category_code)

    elif mode == "review-batch":
        # 배치별 리뷰 수집
        if not product_ids or not batch_info:
            logger.error("PRODUCT_IDS와 BATCH_INFO 환경변수가 필요합니다.")
            exit(1)
        result = pipeline.run_review_batch(product_ids, batch_info)

    elif mode == "create-batches":
        # product_ids를 배치로 나누기
        if not product_ids or not category_code:
            logger.error("PRODUCT_IDS와 CATEGORY_CODE 환경변수가 필요합니다.")
            exit(1)
        result = pipeline.create_review_batches_from_ids(product_ids, category_code, batch_size)

    logger.info(f"크롤링 결과: {result}")

    # 결과를 JSON으로 출력 (Airflow에서 XCom으로 활용 가능)
    print(json.dumps(result, ensure_ascii=False, indent=2))

    # 결과에 따라 exit code 설정
    if result.get("status") == "success":
        logger.info("크롤링 작업이 성공적으로 완료되었습니다.")
        exit(0)
    else:
        logger.error("크롤링 작업이 실패했습니다.")
        exit(1)


if __name__ == "__main__":
    main()
