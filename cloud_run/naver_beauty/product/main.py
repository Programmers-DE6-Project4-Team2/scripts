# main.py
import argparse
from naver_beauty_crawler import collect_product

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="네이버 단일 카테고리 상품 수집기")
    parser.add_argument("--bucket", required=True, help="GCS bucket name")
    parser.add_argument("--category", required=True, help="카테고리 이름 (예: skincare)")
    args = parser.parse_args()

    collect_product(args.bucket, args.category)
