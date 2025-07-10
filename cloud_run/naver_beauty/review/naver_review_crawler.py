import argparse
import logging
import sys
import time
import os
from typing import List, Dict
from datetime import datetime
import pandas as pd
import tempfile

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from gcs_uploader import upload_to_gcs

# ✅ 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

# ✅ 리뷰 파싱 함수
def parse_review_element(element) -> Dict:
    def safe_find(selector, by=By.CSS_SELECTOR, many=False):
        try:
            return (element.find_elements if many else element.find_element)(by, selector)
        except:
            return [] if many else None

    review_id = element.get_attribute("data-shp-contents-id")
    username = safe_find("strong._2L3vDiadT9")
    username = username.text.strip() if username else None

    date_spans = safe_find("span._2L3vDiadT9", many=True)
    created_at = next((s.text.strip() for s in date_spans if "." in s.text), None)

    rating = safe_find("em._15NU42F3kT")
    rating = rating.text.strip() if rating else None

    content = None
    try:
        content_element = element.find_element(By.CSS_SELECTOR, "div._1kMfD5ErZ6 > span._2L3vDiadT9")
        content = content_element.text.strip()
    except:
        try:
            fallback = element.find_element(By.CSS_SELECTOR, "div._3z6gI4oI6l")
            content = fallback.text.strip()
        except:
            content = None

    option = safe_find("div._2FXNMst_ak")
    option = option.text.strip() if option else None

    image_tag = safe_find("img[src*='checkout.phinf']")
    image_url = image_tag.get_attribute("src") if image_tag else None

    return {
        "review_id": review_id,
        "username": username,
        "created_at": created_at,
        "rating": rating,
        "content": content,
        "option": option,
        "image_url": image_url
    }

# ✅ 리뷰 추출
def extract_reviews_from_page(driver) -> List[Dict]:
    reviews = []
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li.BnwL_cs1av"))
        )
        time.sleep(3)
    except Exception as e:
        logging.warning(f"⚠️ 리뷰 요소 로딩 실패 - 예외: {e}")
        time.sleep(3)

    review_elements = driver.find_elements(By.CSS_SELECTOR, "li.BnwL_cs1av")
    logging.info(f"🔎 현재 리뷰 요소 수: {len(review_elements)}")

    for element in review_elements:
        try:
            more_span = element.find_elements(By.CSS_SELECTOR, "span._3R1ftMxgoY")
            if more_span:
                driver.execute_script("arguments[0].click();", more_span[0])
                time.sleep(0.1)

            review = parse_review_element(element)
            if review.get("content"):
                reviews.append(review)
        except:
            continue
    return reviews

# ✅ 리뷰 수집 함수
def collect_and_save(product_id: str, category_name: str, product_url: str, bucket_name: str, timestamp: str, max_reviews: int = 1000):
    logging.info(f"🔍 리뷰 수집 시작: [{category_name}] {product_id}")
    reviews = []
    seen = set()
    prev_first_id = None

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(options=options)

    try:
        driver.get(product_url)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(2)

        try:
            review_tab = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, '//a[contains(text(), "리뷰")]'))
            )
            review_tab.click()
            WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li.BnwL_cs1av"))
            )
            time.sleep(2)
        except:
            logging.warning(f"❌ 리뷰 탭 클릭 실패: {product_id}")
            return

        page = 1
        while len(reviews) < max_reviews:
            logging.info(f"🔎 페이지 {page} 리뷰 추출 시작")
            new_reviews = extract_reviews_from_page(driver)
            if not new_reviews:
                logging.info(f"📭 새 리뷰 없음 또는 마지막 페이지 도달 (페이지 {page})")
                break

            curr_first_id = new_reviews[0].get("review_id") if new_reviews else None
            if curr_first_id == prev_first_id:
                logging.warning(f"⚠️ 페이지 {page} 내용 동일 → 중단")
                break
            prev_first_id = curr_first_id

            for r in new_reviews:
                rid = r.get("review_id", "")
                if rid and rid not in seen:
                    seen.add(rid)
                    reviews.append(r)
            logging.info(f"📄 페이지 {page}에서 {len(new_reviews)}개 리뷰 추출됨")
            logging.info(f"🔁 페이지 {page}까지 수집됨 - 총 리뷰 수: {len(reviews)})")

            if len(reviews) >= max_reviews:
                break

            try:
                next_btn = driver.find_element(By.XPATH, '//a[text()="다음"]')
                if "disabled" in next_btn.get_attribute("class") or not next_btn.is_displayed():
                    break
                driver.execute_script("arguments[0].click();", next_btn)
                WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li.BnwL_cs1av"))
                )
                time.sleep(3)
                page += 1
            except:
                break

    except Exception as e:
        logging.error(f"❌ 수집 중 예외 발생: {product_id} - {e}")
    finally:
        driver.quit()
        save_reviews(reviews, bucket_name, category_name, product_id, timestamp, max_reviews)

# ✅ GCS 저장 함수
def save_reviews(reviews: List[Dict], bucket_name: str, category_name: str, product_id: str, timestamp: str, max_reviews: int):
    if not reviews:
        logging.warning(f"⚠️ 수집된 리뷰 없음: {product_id}")
        return

    df = pd.DataFrame(reviews[:max_reviews])
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", encoding="utf-8-sig", delete=False) as tmp:
        df.to_csv(tmp.name, index=False)
        tmp_path = tmp.name

    blob_path = f"raw-data/naver/{category_name}/reviews/{timestamp}/{product_id}_reviews.csv"
    upload_to_gcs(bucket_name, content=tmp_path, blob_path=blob_path, content_type="text/csv", from_bytes=False)
    logging.info(f"📤 업로드 완료: gs://{bucket_name}/{blob_path}")
    os.remove(tmp_path)

# ✅ 실행 진입점
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
        max_reviews=1000
    )
