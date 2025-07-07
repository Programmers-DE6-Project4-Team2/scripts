import os
import json
import time
from typing import List, Dict
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

    username = safe_find("strong._2L3vDiadT9")
    username = username.text.strip() if username else None

    date_spans = safe_find("span._2L3vDiadT9", many=True)
    created_at = next((s.text.strip() for s in date_spans if "." in s.text), None)

    rating = safe_find("em._15NU42F3kT")
    rating = rating.text.strip() if rating else None

    # 본문 추출 (더보기 있는 경우와 없는 경우 모두 커버)
    content = None
    try:
        content_element = element.find_element(By.CSS_SELECTOR, "div._3bcnBc6TBC > span._2L3vDiadT9")
        content = content_element.text.strip()
    except:
        try:
            fallback_element = element.find_element(By.CSS_SELECTOR, "div._3z6gI4oI6l")
            content = fallback_element.text.strip()
        except:
            content = None

    option = safe_find("div._2FXNMst_ak")
    option = option.text.strip() if option else None

    image_tag = safe_find("img[src*='checkout.phinf']")
    image_url = image_tag.get_attribute("src") if image_tag else None

    print("\n📄 리뷰 디버그:")
    print("  작성자:", username)
    print("  날짜:", created_at)
    print("  평점:", rating)
    print("  옵션:", option)
    print("  이미지:", image_url)
    print("  본문:", repr(content))

    return {
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

def collect_and_save_reviews(product_id: str, category_name: str, product_url: str, max_reviews: int = 500):
    print(f"\n📦 [{category_name}] {product_id} 리뷰 수집 시작")
    options = Options()
    # options.add_argument("--headless=new")
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

        while len(reviews) < max_reviews and page_count < 30:
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

        save_dir = os.path.join("collected_review", category_name)
        os.makedirs(save_dir, exist_ok=True)
        save_path = os.path.join(save_dir, f"{product_id}.json")

        with open(save_path, "w", encoding="utf-8") as f:
            json.dump({
                "product_id": product_id,
                "category": category_name,
                "review_count": len(reviews),
                "reviews": reviews[:max_reviews]
            }, f, ensure_ascii=False, indent=2)

        print(f"💾 저장 완료: {save_path}")

    except Exception as e:
        print(f"❌ 오류: {product_id} - {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    collect_and_save_reviews(
        product_id="10661966119",
        category_name="스킨케어",
        product_url="https://shopping.naver.com/window-products/beauty/10661966119"
    )
