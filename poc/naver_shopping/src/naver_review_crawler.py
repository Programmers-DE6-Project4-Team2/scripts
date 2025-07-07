import os
import json
import time
import csv
import sys
from typing import List, Dict
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

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

def extract_reviews_from_page(driver) -> List[Dict]:
    reviews = []
    try:
        WebDriverWait(driver, 10).until(
            lambda d: len(d.find_elements(By.CSS_SELECTOR, "li.BnwL_cs1av")) > 0
        )
    except:
        print("⚠️ 리뷰 요소 로딩 실패 (10초 안에 요소 없음)")

    review_elements = driver.find_elements(By.CSS_SELECTOR, "li.BnwL_cs1av")
    print(f"🧪 감지된 리뷰 요소 수: {len(review_elements)}")

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

def save_reviews_to_csv(reviews: List[Dict], csv_path: str):
    keys = ["review_id", "username", "created_at", "rating", "content", "option", "image_url"]
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(reviews)

def collect_and_save_reviews(product_id: str, category_name: str, product_url: str, collection_time_str: str, max_reviews: int = 1000):
    print(f"\n📦 [{category_name}] {product_id} 리뷰 수집 시작")
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
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
            time.sleep(3)
        except:
            print("❌ 리뷰 탭 클릭 실패")
            return

        reviews = []
        page_count = 0

        while len(reviews) < max_reviews and page_count < 50:
            print(f"👉 페이지 {page_count + 1} | 누적 리뷰 수: {len(reviews)}")
            new_reviews = extract_reviews_from_page(driver)

            if len(new_reviews) == 0:
                print("🚫 새로운 리뷰 없음 → 종료")
                break

            reviews.extend(new_reviews)
            seen = set()
            unique_reviews = []
            for r in reviews:
                c = r.get("content", "")
                if c not in seen:
                    seen.add(c)
                    unique_reviews.append(r)
            reviews = unique_reviews

            if len(reviews) >= max_reviews:
                break

            try:
                next_btn = driver.find_element(By.XPATH, '//a[text()="다음"]')
                if "disabled" in next_btn.get_attribute("class") or not next_btn.is_displayed():
                    print("📭 다음 버튼 비활성 상태 → 종료")
                    break
                print("➡ 다음 페이지 이동")
                driver.execute_script("arguments[0].click();", next_btn)
                time.sleep(2)
                page_count += 1
            except Exception as e:
                print(f"❌ 다음 버튼 탐색 실패 → 종료: {e}")
                break

        print(f"✅ 수집 완료: {len(reviews)}개")

        base_dir = os.path.dirname(os.path.abspath(__file__))
        save_dir = os.path.join(base_dir, "collected_review", collection_time_str, category_name)
        os.makedirs(save_dir, exist_ok=True)

        json_path = os.path.join(save_dir, f"{product_id}.json")
        csv_path = os.path.join(save_dir, f"{product_id}.csv")

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump({
                "product_id": product_id,
                "category": category_name,
                "review_count": len(reviews),
                "reviews": reviews[:max_reviews]
            }, f, ensure_ascii=False, indent=2)

        save_reviews_to_csv(reviews[:max_reviews], csv_path)

        print(f"💾 저장 완료: {json_path}, {csv_path}")

    except Exception as e:
        print(f"❌ 오류: {product_id} - {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    if len(sys.argv) == 3:
        csv_path = sys.argv[1]
        category_name = sys.argv[2]
        if not os.path.exists(csv_path):
            print(f"❌ 파일을 찾을 수 없습니다: {csv_path}")
            sys.exit(1)

        collection_time_str = datetime.now().strftime("%Y%m%d_%H%M")

        with open(csv_path, newline='', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            reader.fieldnames = [h.strip() for h in reader.fieldnames]  # ← 다시 strip (필수!)
            for row in reader:
                pid = row["product_id"]
                url = row["product_url"]
                print(f"\n--- {pid} 수집 중 ---")
                collect_and_save_reviews(product_id=pid, category_name=category_name, product_url=url, collection_time_str=collection_time_str)
    else:
        print("사용법:")
        print("  python naver_review_crawler.py <csv_path> <category_name>") # python naver_review_crawler.py collected_data/20250703_125653/스킨케어_20006492.csv 스킨케어