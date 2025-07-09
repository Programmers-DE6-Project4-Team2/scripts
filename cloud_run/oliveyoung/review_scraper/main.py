"""
올리브영 리뷰 크롤러 - Cloud Run Job
특정 상품의 리뷰 데이터를 수집하여 GCS에 저장
"""

import sys
import json
import logging
import argparse
from datetime import datetime, timezone
from oliveyoung_review_scraper_module import OliveYoungReviewScraper
from gcs_uploader import GCSUploader

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def parse_arguments():
    """커맨드 라인 인자 파싱"""
    parser = argparse.ArgumentParser(description='Olive Young Review Scraper')
    parser.add_argument('--product-id', required=True, help='상품 ID')
    parser.add_argument('--url', required=True, help='상품 URL')
    parser.add_argument('--max-pages', type=int, default=1, help='최대 페이지 수 (기본값: 1)')
    
    return parser.parse_args()

def scrape_reviews(product_id: str, product_url: str, max_pages: int = 1):
    """리뷰 크롤링 메인 함수"""
    try:
        # 기본값 설정
        product_name = ""
        
        logger.info(f"Starting review scraping for product ID: {product_id}")
        logger.info(f"URL: {product_url}")
        logger.info(f"Max pages: {max_pages}")
        
        # 크롤링 시작
        scraper = OliveYoungReviewScraper()
        
        try:
            crawling_started_at = datetime.now(timezone.utc).isoformat()
            crawling_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            
            # 리뷰 데이터 크롤링
            reviews, category_name = scraper.extract_reviews_with_pagination(product_url, max_pages)
            
            if not reviews:
                logger.warning(f"No reviews found for product ID: {product_id}")
                return {
                    "status": "completed",
                    "product_id": product_id,
                    "product_name": product_name,
                    "reviews_count": 0,
                    "message": "No reviews found"
                }
            
            # 실제 상품명을 첫 번째 리뷰에서 가져오기
            if reviews and 'product_name' in reviews[0]:
                product_name = reviews[0]['product_name']
            
            # 각 리뷰에 기본 메타데이터 추가 (리뷰 데이터 레벨에서)
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
            
            # GCS에 업로드
            gcs_uploader = GCSUploader()
            
            # 파일 경로 생성 (CSV 확장자로 변경)
            now = datetime.now(timezone.utc)
            file_path = (
                f"raw-data/olive-young/reviews/{product_id}/{product_id}_{now.strftime('%Y%m%d_%H%M%S')}.csv"
            )
            
            # CSV 업로드 (메타데이터 객체 없이 리뷰 데이터만)
            upload_result = gcs_uploader.upload_csv(reviews, file_path)
            
            logger.info(f"Successfully scraped {len(reviews)} reviews for product ID: {product_id}")
            logger.info(f"Product name: {product_name}")
            logger.info(f"Data uploaded to: {upload_result['gcs_path']}")
            
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
        logger.error(f"Error during review scraping: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

def main():
    """메인 실행 함수"""
    try:
        args = parse_arguments()
        
        result = scrape_reviews(
            product_id=args.product_id,
            product_url=args.url,
            max_pages=args.max_pages
        )
        
        # 결과 출력
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        # 성공/실패에 따른 exit code 설정
        if result["status"] == "completed":
            sys.exit(0)
        else:
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Main execution error: {str(e)}", exc_info=True)
        print(json.dumps({
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }, indent=2, ensure_ascii=False))
        sys.exit(1)

if __name__ == '__main__':
    main()
