import os
from datetime import datetime, timezone
from naver_review_crawler import collect_and_save

def get_env_var(name: str, required=True, default: str = None) -> str:
    value = os.getenv(name, default)
    if required and not value:
        raise ValueError(f"❌ 환경 변수 '{name}'가 설정되지 않았습니다.")
    return value

if __name__ == "__main__":
    # ✅ 환경 변수로부터 값 읽기
    product_id = get_env_var("PRODUCT_ID")
    product_url = get_env_var("PRODUCT_URL")
    category = get_env_var("CATEGORY")
    bucket_name = get_env_var("BUCKET_NAME")
    sort_type = get_env_var("REVIEW_SORT", required=False, default="최신순")  # 🔹 기본은 최신순

    # ✅ 타임스탬프 생성
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")

    # ✅ 리뷰 수집 실행
    collect_and_save(
        product_id=product_id,
        category_name=category,
        product_url=product_url,
        bucket_name=bucket_name,
        timestamp=timestamp,
        max_reviews=200,
        sort_option=sort_type 
    )
