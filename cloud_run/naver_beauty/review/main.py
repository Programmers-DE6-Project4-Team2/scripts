# run_review_crawler.py
import argparse
from datetime import datetime
from naver_review_crawler import collect_and_save

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--bucket", required=True, help="GCS 버킷 이름")
    parser.add_argument("--category", required=True, help="카테고리 이름 (예: skincare)")
    parser.add_argument("--product-id", required=True, help="상품 ID")
    parser.add_argument("--product-url", required=True, help="상품 상세 페이지 URL")
    args = parser.parse_args()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M")

    collect_and_save(
        product_id=args.product_id,
        category_name=args.category,
        product_url=args.product_url,
        bucket_name=args.bucket,
        timestamp=timestamp,
        max_reviews=200  # 🔁 매번 200개씩만 수집
    )
