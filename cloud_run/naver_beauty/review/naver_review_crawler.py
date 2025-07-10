import logging
import sys
import time
import os
import tempfile
from typing import List, Dict
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

# ✅ 요소 로딩 여부 판단
def elements_loaded(driver, selector: str) -> bool:
    try:
        elements = driver.find_elements(By.CSS_SELECTOR, selector)
        return len(elements) > 0 and any(e.text.strip() for e in elements)
    except Exception as e:
        logging.warning(f"❌ elements_loaded() 내부 오류: {e}")
        return False

# ✅ 공통 대기 함수
def wait_for_elements(driver, selector: str, timeout: int = 15, wait_time: float = 3) -> bool:
    start = time.time()
    try:
        WebDriverWait(driver, timeout).until(lambda d: elements_loaded(d, selector))
        time.sleep(wait_time)
        return True
    except TimeoutException:
        logging.warning(f"⚠️ 요소 로딩 실패: {selector}")
        return False

# ✅ 리뷰 정렬 옵션 클릭 함수
def click_sort_option(driver, text: str = "최신순"):
    try:
        sort_button = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, f'//ul[contains(@class, "KQTUBC8Cw8")]//a[text()="{text}"]'))
        )
        driver.execute_script("arguments[0].click();", sort_button)
        # logging.info(f"✅ 리뷰 정렬 '{text}' 클릭 완료")
        time.sleep(2)
    except Exception as e:
        logging.warning(f"⚠️ 리뷰 정렬 '{text}' 클릭 실패: {e}")

# ✅ 리뷰 파싱
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
        "rating": rating,
        "content": content,
        "option": option
    }

# ✅ 한 페이지 리뷰 추출
def extract_reviews_from_page(driver) -> List[Dict]:
    logging.info("⏳ 리뷰 요소 로딩 대기 중...")
    reviews = []

    if not wait_for_elements(driver, "li.BnwL_cs1av", timeout=15, wait_time=1.5):
        logging.warning("⚠️ 리뷰 요소 로딩 실패 → 페이지 건너뜀")
        return []

    review_elements = driver.find_elements(By.CSS_SELECTOR, "li.BnwL_cs1av")

    for element in review_elements:
        try:
            more_span = element.find_elements(By.CSS_SELECTOR, "span._3R1ftMxgoY")
            if more_span:
                driver.execute_script("arguments[0].click();", more_span[0])
                time.sleep(0.1)

            review = parse_review_element(element)
            if review.get("content"):
                reviews.append(review)
        except Exception as e:
            logging.warning(f"❌ 리뷰 파싱 실패: {e}")
            continue

    return reviews

# ✅ 전체 리뷰 수집 흐름
def collect_and_save(product_id: str, category_name: str, product_url: str,
                     bucket_name: str, timestamp: str, max_reviews: int = 200):
    logging.info(f"🔍 리뷰 수집 시작: [{category_name}] {product_id}")
    reviews = []
    MAX_PAGES = 20

    for page in range(1, MAX_PAGES + 1):
        if len(reviews) >= max_reviews:
            logging.info("✅ 최대 리뷰 수 도달 → 종료")
            break

        logging.info(f"🔁 [페이지 {page}] 수집을 위한 드라이버 초기화")

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

            # 리뷰 탭 클릭
            try:
                review_tab = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, '//a[contains(text(), "리뷰")]'))
                )
                try:
                    review_tab.click()
                except:
                    driver.execute_script("arguments[0].click();", review_tab)
                time.sleep(2)

                # ✅ 정렬: 최신순 클릭
                click_sort_option(driver, text="최신순")

            except TimeoutException:
                logging.warning(f"❌ 리뷰 탭 클릭 실패: {product_id} → 페이지 {page} 건너뜀")
                continue

            # "다음" 버튼 page-1번 클릭
            for _ in range(1, page):
                try:
                    next_btn = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, '//a[text()="다음"]'))
                    )
                    driver.execute_script("arguments[0].click();", next_btn)
                    time.sleep(1.5)
                except Exception as e:
                    logging.warning(f"⚠️ 페이지 {page} 이동 중 '다음' 버튼 클릭 실패: {e}")
                    break

            logging.info(f"🔎 페이지 {page} 리뷰 추출 시작")
            new_reviews = extract_reviews_from_page(driver)

            if not new_reviews:
                logging.warning(f"⚠️ 페이지 {page}에서 리뷰 없음 또는 로딩 실패 → 건너뜀")
                continue

            reviews.extend(new_reviews)
            #logging.info(f"📄 페이지 {page}에서 {len(new_reviews)}개 리뷰 추출됨")
            logging.info(f"🔁 총 누적 리뷰 수: {len(reviews)}")

        except Exception as e:
            logging.error(f"❌ 페이지 {page} 처리 중 예외 발생: {e}")
            continue
        finally:
            driver.quit()

    save_reviews(reviews, bucket_name, category_name, product_id, timestamp, max_reviews)

# ✅ 결과 저장
def save_reviews(reviews: List[Dict], bucket_name: str, category_name: str,
                 product_id: str, timestamp: str, max_reviews: int):
    if not reviews:
        logging.warning(f"⚠️ 수집된 리뷰 없음: {product_id}")
        return

    df = pd.DataFrame(reviews[:max_reviews])
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", encoding="utf-8-sig", delete=False) as tmp:
        df.to_csv(tmp.name, index=False)
        tmp_path = tmp.name

    blob_path = f"raw-data/naver/{category_name}/reviews/{product_id}/{timestamp}_reviews.csv"
    upload_to_gcs(bucket_name, content=tmp_path, blob_path=blob_path, content_type="text/csv", from_bytes=False)
    logging.info(f"📤 업로드 완료: gs://{bucket_name}/{blob_path}")
    os.remove(tmp_path)
