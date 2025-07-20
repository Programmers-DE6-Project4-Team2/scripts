# 전체 코드
import logging
import sys
import os
import time
import tempfile
from typing import List, Dict
from datetime import datetime, timezone
import pandas as pd

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from gcs_uploader import upload_to_gcs

# ✅ 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

def elements_loaded(driver, selector: str) -> bool:
    try:
        elements = driver.find_elements(By.CSS_SELECTOR, selector)
        return len(elements) > 0 and any(e.text.strip() for e in elements)
    except Exception as e:
        logging.warning(f"❌ elements_loaded() 내부 오류: {e}")
        return False

def wait_for_elements(driver, selector: str, timeout: int = 15, wait_time: float = 3) -> bool:
    try:
        WebDriverWait(driver, timeout).until(lambda d: elements_loaded(d, selector))
        time.sleep(wait_time)
        return True
    except TimeoutException:
        logging.warning(f"⚠️ 요소 로딩 실패: {selector}")
        return False

def click_sort_option(driver, text: str = "최신순"):
    try:
        sort_button = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, f'//ul[contains(@class, "KQTUBC8Cw8")]//a[text()="{text}"]'))
        )
        driver.execute_script("arguments[0].click();", sort_button)
        time.sleep(2)
    except Exception as e:
        logging.warning(f"⚠️ 리뷰 정렬 '{text}' 클릭 실패: {e}")

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

    return {
        "review_id": review_id,
        "username": username,
        "created_at": created_at,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "rating": rating,
        "content": content,
        "option": option
    }

def extract_reviews_from_page(driver, category_name: str, product_id: str, sort_option: str) -> List[Dict]:
    if not wait_for_elements(driver, "li.BnwL_cs1av", timeout=15, wait_time=1.5):
        logging.warning("⚠️ 리뷰 요소 로딩 실패 → 페이지 건너뜀")
        return []

    review_elements = driver.find_elements(By.CSS_SELECTOR, "li.BnwL_cs1av")
    reviews = []

    for element in review_elements:
        try:
            more_span = element.find_elements(By.CSS_SELECTOR, "span._3R1ftMxgoY")
            if more_span:
                driver.execute_script("arguments[0].click();", more_span[0])
                time.sleep(0.1)

            review = parse_review_element(element)
            if review.get("content"):
                review["category"] = category_name
                review["product_id"] = product_id
                review["sort_option"] = sort_option
                reviews.append(review)
        except Exception as e:
            logging.warning(f"❌ 리뷰 파싱 실패: {e}")
            continue

    return reviews

def collect_and_save(product_id: str, category_name: str, product_url: str,
                     bucket_name: str, timestamp: str, max_reviews: int = 100, sort_option: str = "랭킹순"):
    logging.info(f"🔍 리뷰 수집 시작: [{category_name}] {product_id}")
    reviews = []
    MAX_PAGES = 10
    empty_page_streak = 0
    MAX_EMPTY_PAGES = 3

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--blink-settings=imagesEnabled=false")
    options.add_argument("--disable-background-networking")
    options.add_argument("--disable-sync")
    options.add_argument("--disable-translate")
    options.add_argument("--disable-features=NetworkService")
    options.add_argument("--no-first-run")

    driver = webdriver.Chrome(options=options)

    try:
        driver.get(product_url)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(2)

        try:
            review_tab = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, '//a[contains(text(), "리뷰")]'))
            )
            try:
                review_tab.click()
            except:
                driver.execute_script("arguments[0].click();", review_tab)
            time.sleep(2)

            click_sort_option(driver, text=sort_option)
        except TimeoutException:
            logging.warning(f"❌ 리뷰 탭 클릭 실패: {product_id}")
            return

        for page in range(1, MAX_PAGES + 1):
            if len(reviews) >= max_reviews:
                logging.info("✅ 최대 리뷰 수 도달 → 종료")
                break

            logging.info(f"🔎 페이지 {page} 리뷰 추출 시작")
            new_reviews = extract_reviews_from_page(driver, category_name, product_id, sort_option)

            if not new_reviews:
                empty_page_streak += 1
                logging.warning(f"⚠️ 페이지 {page} 리뷰 없음 (연속 없음 {empty_page_streak}회)")
                if empty_page_streak >= MAX_EMPTY_PAGES:
                    logging.warning("🚫 연속 빈 페이지 3회 → 종료")
                    break
                continue
            else:
                empty_page_streak = 0

            reviews.extend(new_reviews)
            logging.info(f"🔁 총 누적 리뷰 수: {len(reviews)}")

            try:
                next_btn = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, '//a[text()="다음"]'))
                )
                driver.execute_script("arguments[0].click();", next_btn)
                time.sleep(1.5)
            except Exception as e:
                logging.warning(f"⚠️ 페이지 {page} → 다음 클릭 실패: {e}")
                break

    except Exception as e:
        logging.error(f"❌ 수집 중 예외 발생: {e}")
    finally:
        driver.quit()

    if not reviews:
        logging.info(f"🧩 리뷰 없음 → 저장 없이 종료: {product_id}")
        return

    save_reviews(reviews, bucket_name, category_name, product_id, timestamp, max_reviews)

def save_reviews(reviews: List[Dict], bucket_name: str, category_name: str,
                 product_id: str, timestamp: str, max_reviews: int):
    df = pd.DataFrame(reviews[:max_reviews])
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", encoding="utf-8-sig", delete=False) as tmp:
        df.to_csv(tmp.name, index=False)
        tmp_path = tmp.name

    dt = datetime.strptime(timestamp, "%Y%m%d_%H%M")
    year = dt.strftime("%Y")
    month = dt.strftime("%m")
    day = dt.strftime("%d")

    blob_path = f"raw-data/naver/reviews/{product_id}/{year}/{month}/{day}/{product_id}_{timestamp}.csv"
    upload_to_gcs(bucket_name, content=tmp_path, blob_path=blob_path, content_type="text/csv", from_bytes=False)
    logging.info(f"📤 업로드 완료: gs://{bucket_name}/{blob_path}")
    os.remove(tmp_path)
