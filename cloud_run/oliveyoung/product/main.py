import os
import sys
import logging
from datetime import datetime, timezone
import pandas as pd
from google.cloud import storage
from oliveyoung_crawler_module import OliveYoungProductCrawler
from dotenv import load_dotenv

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
load_dotenv()


def upload_csv_to_gcs(bucket_name: str, dataframe: pd.DataFrame, destination_blob_name: str):
    logger.info("🔄 [GCS] 업로드 시작...")
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    csv_data = dataframe.to_csv(index=False, encoding="utf-8-sig")
    logger.info(f"🔄 [GCS] CSV 변환 완료, 크기: {len(csv_data)} bytes")
    blob.upload_from_string(csv_data, content_type="text/csv")
    logger.info(f"✅ [GCS] 업로드 완료: gs://{bucket_name}/{destination_blob_name}")
    return f"gs://{bucket_name}/{destination_blob_name}"


def main():
    # 명령행 인수 처리
    if len(sys.argv) >= 4:
        category_name = sys.argv[1]
        category_url = sys.argv[2]
        max_pages = int(sys.argv[3])
    else:
        # 환경변수 로드 (fallback)
        category_url = os.getenv("CATEGORY_URL")
        category_name = os.getenv("CATEGORY_NAME", "default")
        max_pages = int(os.getenv("MAX_PAGES", "1"))

    bucket_name = os.getenv("BUCKET_NAME", "de6-ez2")

    if not category_url:
        raise ValueError("CATEGORY_URL이 필요합니다. 명령행 인수 또는 환경변수로 제공하세요.")

    logger.info(f"[START] category={category_name} max_pages={max_pages}")
    crawler = OliveYoungProductCrawler(headless=True)

    try:
        # 1. 크롤링
        products = crawler.extract_product_list(category_url, max_pages=max_pages)
        df = pd.DataFrame(products)

        # 2. GCS 업로드
        now = datetime.now(timezone.utc)
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        year = now.strftime("%Y")
        month = now.strftime("%m")
        day = now.strftime("%d")
        filename = f"raw-data/olive-young/products/{category_name}/{year}/{month}/{day}/{category_name}_{timestamp}.csv"
        gcs_path = upload_csv_to_gcs(bucket_name, df, filename)

        # 3. 완료 로그
        logger.info(f"🎉 작업 완료: {len(products)}개 상품, 경로: {gcs_path}")

    except Exception as e:
        logger.exception("크롤링 도중 에러 발생")
        raise

    finally:
        crawler.close()

if __name__ == "__main__":
    main()
