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

from musinsa_crawler import MusinsaCrawler
from musinsa_review_collector import MusinsaReviewCollector
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
        job_type = os.environ.get("JOB_TYPE", "product")
        logger.info(f"Job type: {job_type}")

        if job_type == "product":
            result = run_product_job()
        elif job_type == "review":
            result = run_review_job()
        else:
            raise ValueError(f"Unknown job type: {job_type}")

        # Airflow XCom용 JSON 출력
        print(json.dumps(result, ensure_ascii=False))

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
            "job_type": os.environ.get("JOB_TYPE", "unknown")
        }
        print(json.dumps(error_result, ensure_ascii=False))
        logger.error(f"작업 실패: {str(e)}")
        sys.exit(1)


def run_product_job():
    """카테고리별 상품 크롤링 - Airflow Dynamic Task Mapping 호환"""
    category_code = os.environ.get("CATEGORY_CODE", "104001")
    max_pages = int(os.environ.get("MAX_PAGES", "8"))

    logger.info(f"상품 크롤링 시작 - category: {category_code}")

    crawler = MusinsaCrawler(
        section_id="231",
        size=40,
        max_pages=max_pages,
        review_page_size=20,
        review_max_pages=1
    )

    # 카테고리별 크롤링 실행
    result = crawler.crawl_single_category_ranking(category_code)

    # GCS 업로드
    if result.get('products'):
        success = upload_products_to_gcs(result, category_code)
        result['gcs_uploaded'] = success

    # Airflow Dynamic Task Mapping용 반환값
    return {
        "status": "success",
        "job_type": "product",
        "category_code": category_code,
        "product_ids": result.get('product_ids', []),
        "product_count": result.get('product_count', 0),
        "gcs_uploaded": result.get('gcs_uploaded', False),
        "scraped_at": datetime.now(timezone.utc).isoformat()
    }


def run_review_job():
    """배치별 리뷰 크롤링 - Airflow 배치 처리 호환"""
    product_ids_str = os.environ.get("PRODUCT_IDS", "[]")
    batch_info_str = os.environ.get("BATCH_INFO", "{}")
    review_pages = int(os.environ.get("REVIEW_PAGES", "25"))

    # JSON 파싱
    product_ids = json.loads(product_ids_str)
    batch_info = json.loads(batch_info_str)

    logger.info(f"리뷰 크롤링 시작 - 배치: {batch_info.get('batch_index', 0)}, 상품 수: {len(product_ids)}")

    crawler = MusinsaCrawler(
        section_id="231",
        size=40,
        max_pages=1,
        review_page_size=20,
        review_max_pages=review_pages
    )

    # 배치별 리뷰 크롤링 실행
    result = crawler.crawl_review_batch(product_ids, batch_info)

    # GCS 업로드
    if result.get('reviews'):
        success = upload_reviews_to_gcs(result)
        result['gcs_uploaded'] = success

    return {
        "status": "success",
        "job_type": "review",
        "batch_info": batch_info,
        "category_code": batch_info.get('category_code'),
        "batch_index": batch_info.get('batch_index', 0),
        "review_count": result.get('review_count', 0),
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
        now_utc = datetime.now(timezone.utc)
        year = now_utc.strftime("%Y")
        month = now_utc.strftime("%m")
        day = now_utc.strftime("%d")
        timestamp = now_utc.strftime("%Y%m%d_%H%M%S")

        filename = f"{category_name}_{timestamp}.csv"
        gcs_path = f"raw-data/musinsa/products/{category_name}/{year}/{month}/{day}/{filename}"

        df = pd.DataFrame(result['products'])
        return upload_csv_to_gcs(bucket_name, df, gcs_path, os.environ.get("GCS_PROJECT_ID"))

    except Exception as e:
        logger.error(f"상품 데이터 GCS 업로드 실패: {e}")
        return False


def upload_reviews_to_gcs(result):
    """리뷰 데이터 GCS 업로드"""
    bucket_name = os.environ.get("GCS_BUCKET_NAME")
    if not bucket_name or bucket_name == "your-bucket-name":
        return False

    try:
        # 리뷰 데이터 플랫하게 변환
        temp_collector = MusinsaReviewCollector(None, [])
        review_rows = temp_collector.flatten_reviews(result['reviews'])
        if not review_rows:
            logger.warning("업로드할 리뷰 데이터가 없습니다.")
            return True

        now_utc = datetime.now(timezone.utc)
        year = now_utc.strftime("%Y")
        month = now_utc.strftime("%m")
        day = now_utc.strftime("%d")
        timestamp = now_utc.strftime("%Y%m%d_%H%M%S")

        # 상품별로 리뷰 그룹화
        product_reviews = {}
        for review in review_rows:
            product_id = review.get('product_id', 'unknown')
            if product_id not in product_reviews:
                product_reviews[product_id] = []
            product_reviews[product_id].append(review)

        uploaded_files = []
        # 각 상품별로 개별 파일 업로드
        for product_id, reviews in product_reviews.items():
            filename = f"{product_id}_{timestamp}.csv"
            gcs_path = f"raw-data/musinsa/reviews/{product_id}/{year}/{month}/{day}/{filename}"

            df = pd.DataFrame(reviews)
            success = upload_csv_to_gcs(bucket_name, df, gcs_path, os.environ.get("GCS_PROJECT_ID"))

            if success:
                uploaded_files.append(gcs_path)
                logger.info(f"상품 {product_id} 리뷰 업로드 완료: {len(reviews)}개")

        return len(uploaded_files) > 0

    except Exception as e:
        logger.error(f"리뷰 데이터 GCS 업로드 실패: {e}")
        return False


if __name__ == "__main__":
    main()
