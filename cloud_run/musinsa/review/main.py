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

from musinsa_crawler import MusinsaReviewCrawler
from utils import CATEGORY_MAPPING
from gcs_uploader import upload_csv_to_gcs

# 로깅 설정
logging.basicConfig(
    level=getattr(logging, os.environ.get("LOG_LEVEL", "INFO")),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """메인 함수 - 단일 상품 리뷰 크롤링"""
    try:
        # 환경변수에서 필수 파라미터 가져오기
        product_id = os.environ.get("PRODUCT_ID")
        if not product_id:
            raise ValueError("PRODUCT_ID 환경변수가 설정되지 않았습니다.")

        logger.info(f"상품 {product_id}의 리뷰 크롤링 시작")

        result = run_review_job(product_id)

        if result.get("status") == "success":
            logger.info("작업이 성공적으로 완료되었습니다.")
            print(json.dumps(result, ensure_ascii=False, indent=2))
            sys.exit(0)
        else:
            logger.error("작업이 실패했습니다.")
            print(json.dumps(result, ensure_ascii=False, indent=2))
            sys.exit(1)

    except Exception as e:
        error_result = {
            "status": "error",
            "error_message": str(e),
            "job_type": "review",
            "product_id": os.environ.get("PRODUCT_ID", "unknown")
        }
        print(json.dumps(error_result, ensure_ascii=False))
        logger.error(f"작업 실패: {str(e)}")
        sys.exit(1)

def run_review_job(product_id: str):
    try:
        category_code = os.environ.get("CATEGORY_CODE", "104001")
        category_name = CATEGORY_MAPPING.get(category_code, "")
        product_id = os.environ.get("PRODUCT_ID", "")
        review_pages = int(os.environ.get("REVIEW_PAGES", "25"))
        sort = os.environ.get("SORT", "up_cnt_desc")
        my_filter = os.environ.get("MY_FILTER", "false")
        has_photo = os.environ.get("HAS_PHOTO", "false")
        is_experience = os.environ.get("IS_EXPERIENCE", "false")
        request_delay = float(os.environ.get("REQUEST_DELAY", "1.0"))

        logger.info(f"리뷰 크롤링 시작 - category {category_name}의 {product_id}")

        # 크롤러 초기화
        crawler = MusinsaReviewCrawler(
            product_id=product_id,
            category_code=category_code,
            review_page_size=20,
            review_max_pages=review_pages,
            sort=sort,
            my_filter=my_filter,
            has_photo=has_photo,
            is_experience=is_experience,
            request_delay=request_delay
        )

        # 리뷰 크롤링 실행
        result = crawler.crawl_reviews()

        # GCS 업로드
        if result.get('reviews'):
            gcs_success = upload_reviews_to_gcs(result)
            result['gcs_uploaded'] = gcs_success
        else:
            result['gcs_uploaded'] = False

        return {
            "status": "success",
            "job_type": "review",
            "product_id": product_id,
            "category_code": category_code,
            "category_name": category_name,
            "review_count": result.get('review_count', 0),
            "gcs_uploaded": result.get('gcs_uploaded', False),
            "scraped_at": result.get('scraped_at')
        }

    except Exception as e:
        logger.error(f"리뷰 크롤링 실패: {e}")
        return {
            "status": "error",
            "error_message": str(e),
            "job_type": "review",
            "product_id": product_id
        }


def upload_reviews_to_gcs(result):
    """리뷰 데이터 GCS 업로드"""
    bucket_name = os.environ.get("GCS_BUCKET_NAME")
    if not bucket_name or bucket_name == "your-bucket-name":
        logger.warning("GCS_BUCKET_NAME이 설정되지 않아 업로드를 건너뜁니다.")
        return False

    try:
        product_id = result['product_id']
        reviews = result['reviews']

        if not reviews:
            logger.warning("업로드할 리뷰 데이터가 없습니다.")
            return True

        # 크롤러 인스턴스 생성 (flatten_reviews 메서드 사용을 위해)
        crawler = MusinsaReviewCrawler(
            product_id=product_id,
            category_code=result['category_code']
        )

        # 리뷰 데이터 플랫하게 변환
        review_rows = crawler.flatten_reviews(reviews)

        # 날짜별 경로 생성
        now_utc = datetime.now(timezone.utc)
        year = now_utc.strftime("%Y")
        month = now_utc.strftime("%m")
        day = now_utc.strftime("%d")
        timestamp = now_utc.strftime("%Y%m%d_%H%M%S")

        # GCS 경로 및 파일명 생성
        filename = f"{product_id}_{timestamp}.csv"
        gcs_path = f"raw-data/musinsa/reviews/{product_id}/{year}/{month}/{day}/{filename}"

        # DataFrame으로 변환 후 GCS 업로드
        df = pd.DataFrame(review_rows)
        success = upload_csv_to_gcs(
            bucket_name=bucket_name,
            dataframe=df,
            destination_blob_name=gcs_path,
            project_id=os.environ.get("GCS_PROJECT_ID")
        )

        if success:
            logger.info(f"상품 {product_id} 리뷰 업로드 완료: {len(review_rows)}개")
            return True
        else:
            logger.error(f"상품 {product_id} 리뷰 업로드 실패")
            return False

    except Exception as e:
        logger.error(f"리뷰 데이터 GCS 업로드 실패: {e}")
        return False


if __name__ == "__main__":
    main()