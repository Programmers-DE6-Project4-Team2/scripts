# main.py (환경변수 기반 실행)
import os
import logging
from naver_beauty_crawler import collect_product

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_env_args():
    bucket = os.environ.get("BUCKET_NAME")
    category = os.environ.get("CATEGORY")

    if not bucket or not category:
        raise ValueError("❌ 환경변수 'BUCKET_NAME' 또는 'CATEGORY'가 설정되지 않았습니다.")

    return bucket, category

if __name__ == "__main__":
    logger.info("🚀 네이버 상품 수집 시작")
    try:
        bucket, category = get_env_args()
        logger.info(f"📦 버킷: {bucket} / 📂 카테고리: {category}")
        collect_product(bucket, category)
    except Exception as e:
        logger.error(f"❌ 실행 중 오류 발생: {e}", exc_info=True)
        raise
