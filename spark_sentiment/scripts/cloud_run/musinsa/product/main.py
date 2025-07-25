#!/usr/bin/env python3
"""
무신사 데이터 수집 Cloud Run Job 애플리케이션 (Airflow DAG 통합)
"""

import json
import os
import logging
import sys
from datetime import datetime, timezone
from dotenv import load_dotenv
import pandas as pd

# 로컬 환경일 경우 dotenv 로드
if os.environ.get("ENV", "").lower() != "production":
    load_dotenv()

from musinsa_product_crawler import MusinsaProductCrawler
from utils import CATEGORY_MAPPING
from gcs_uploader import upload_csv_to_gcs

# 로깅 설정
logging.basicConfig(
    level=getattr(logging, os.environ.get("LOG_LEVEL", "INFO")),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """메인 함수 - 환경변수에 따른 실행 모드 결정"""
    try:
        result = run_product_job()

        if result.get("status") == "success":
            logger.info("작업이 성공적으로 완료되었습니다.")
            sys.exit(0)
        else:
            logger.error("작업이 실패했습니다.")
            sys.exit(1)

    except Exception as e:
        error_result = {
            "status": "error",
            "error_message": str(e),
            "job_type": "product"
        }
        print(json.dumps(error_result, ensure_ascii=False))
        logger.error(f"작업 실패: {str(e)}")
        sys.exit(1)


def run_product_job():
    """카테고리별 상품 크롤링"""
    category_code = os.environ.get("CATEGORY_CODE", "104001")
    max_pages = int(os.environ.get("MAX_PAGES", "8"))

    logger.info(f"상품 크롤링 시작 - category: {category_code}")

    crawler = MusinsaProductCrawler(
        section_id="231",
        size=40,
        max_pages=max_pages,
        category_code=category_code
    )

    # 카테고리별 크롤링 실행
    result = crawler.crawl_single_category_ranking()

    # GCS 업로드
    if result.get('products'):
        success = upload_products_to_gcs(result, category_code)
        result['gcs_uploaded'] = success

    # Airflow Dynamic Task Mapping용 반환값
    return {
        "status": "success",
        "job_type": "product",
        "category_code": category_code,
        "gcs_uploaded": result.get('gcs_uploaded', False),
        "scraped_at": datetime.now(timezone.utc).isoformat()
    }


def upload_products_to_gcs(result, category_code):
    """상품 데이터 GCS 업로드"""
    bucket_name = os.environ.get("GCS_BUCKET_NAME")
    if not bucket_name or bucket_name == "your-bucket-name":
        return False

    try:
        category_name = CATEGORY_MAPPING.get(category_code, f"category_{category_code}")
        category_name = category_name.replace("/", "&")
        now_utc = datetime.now(timezone.utc)
        year = now_utc.strftime("%Y")
        month = now_utc.strftime("%m")
        day = now_utc.strftime("%d")
        timestamp = now_utc.strftime("%Y%m%d_%H%M%S")

        filename = f"{category_name}_{timestamp}.csv"
        gcs_path = f"raw-data/musinsa/products/{category_name}/{year}/{month}/{day}/{filename}"

        df = pd.DataFrame(result['products'])
        return upload_csv_to_gcs(
            bucket_name=bucket_name,
            dataframe=df,
            destination_blob_name = gcs_path,
            project_id=os.environ.get("GCS_PROJECT_ID")
        )

    except Exception as e:
        logger.error(f"상품 데이터 GCS 업로드 실패: {e}")
        return False



if __name__ == "__main__":
    main()
