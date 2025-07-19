"""
올리브영 리뷰 크롤러 - Cloud Run Job
특정 상품의 리뷰 데이터를 수집하여 GCS에 저장
"""

import os
import sys
import json
import logging
from datetime import datetime, timezone
from oliveyoung_review_scraper_module import OliveYoungReviewScraper
from gcs_uploader import GCSUploader

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def scrape_reviews(product_id: str, product_url: str, max_pages: int = 1):
    """리뷰 크롤링 메인 함수"""
    try:
        product_name = ""

        logger.info(f"🟢 Start scraping: product_id={product_id}, max_pages={max_pages}")
        logger.info(f"URL: {product_url}")

        scraper = OliveYoungReviewScraper()

        try:
            crawling_started_at = datetime.now(timezone.utc).isoformat()
            crawling_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

            # 리뷰 크롤링
            reviews, category_name = scraper.extract_reviews_with_pagination(product_url, max_pages)

            if not reviews:
                logger.warning(f"No reviews found for product_id={product_id}")
                return {
                    "status": "completed",
                    "product_id": product_id,
                    "product_name": product_name,
                    "reviews_count": 0,
                    "message": "No reviews found"
                }

            # 첫 리뷰에서 상품명 추출
            if 'product_name' in reviews[0]:
                product_name = reviews[0]['product_name']

            # 메타데이터 추가
            for review in reviews:
                review.update({
                    "product_id": product_id,
                    "product_name": product_name,
                    "product_url": product_url,
                    "category_name": category_name,
                    "crawling_timestamp": crawling_started_at,
                    "crawling_date": crawling_date,
                    "source": "oliveyoung",
                    "data_type": "reviews"
                })

            # GCS 업로드
            gcs_uploader = GCSUploader()
            now = datetime.now(timezone.utc)
            year, month, day = now.strftime("%Y"), now.strftime("%m"), now.strftime("%d")
            timestamp = now.strftime("%Y%m%d_%H%M%S")
            file_path = f"raw-data/olive-young/reviews/{product_id}/{year}/{month}/{day}/{product_id}_{timestamp}.csv"

            upload_result = gcs_uploader.upload_csv(reviews, file_path)

            logger.info(f"✅ Scraped {len(reviews)} reviews for {product_name}")
            logger.info(f"📦 Uploaded to: {upload_result['gcs_path']}")

            return {
                "status": "completed",
                "product_id": product_id,
                "product_name": product_name,
                "reviews_count": len(reviews),
                "gcs_path": upload_result['gcs_path']
            }

        finally:
            scraper.close()

    except Exception as e:
        logger.error(f"Error during scraping: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


def main():
    """환경변수로 실행 (Cloud Run 호환)"""
    try:
        # 환경 변수로부터 인자 로드
        product_id = os.environ["PRODUCT_ID"]
        product_url = os.environ["PRODUCT_URL"]
        max_pages = int(os.environ.get("MAX_PAGES", "1"))

        result = scrape_reviews(product_id, product_url, max_pages)

        print(json.dumps(result, indent=2, ensure_ascii=False))

        if result["status"] == "completed":
            sys.exit(0)
        else:
            sys.exit(1)

    except KeyError as e:
        logger.error(f"필수 환경변수 누락: {str(e)}", exc_info=True)
        print(json.dumps({
            "status": "error",
            "error": f"Missing env var: {str(e)}",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }, indent=2, ensure_ascii=False))
        sys.exit(1)

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        print(json.dumps({
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }, indent=2, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
