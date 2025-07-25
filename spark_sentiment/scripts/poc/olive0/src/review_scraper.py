import time
import csv
import os
import re
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from undetected_chromedriver import Chrome, ChromeOptions
from typing import List, Dict

def extract_total_review_count(soup: BeautifulSoup) -> str:
    """Extract total review count from the review tab"""
    try:
        # 리뷰 탭에서 총 리뷰수 추출: 리뷰<span>(10,789)</span>
        review_tab = soup.select_one('a.goods_reputation span')
        if review_tab:
            review_count_text = review_tab.text.strip()
            # 괄호 안의 숫자만 추출 (예: "(10,789)" -> "10,789")
            match = re.search(r'\(([0-9,]+)\)', review_count_text)
            if match:
                return match.group(1)
        return "N/A"
    except Exception as e:
        print(f"총 리뷰수 추출 중 오류 발생: {e}")
        return "N/A"

def write_data(data):
    file_path = "./data/suncream_reviews_score.csv"
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    file_exists = os.path.isfile(file_path)

    with open(file_path, "a", newline='', encoding='utf-8') as fw:
        fieldnames = ["product_name", "star", "review", "skin_type", "date", "purchase_type", "page", "helpful", "total_review_count"]
        writer = csv.DictWriter(fw, fieldnames=fieldnames)

        if not file_exists:
            writer.writeheader()

        for row in data:
            writer.writerow(row)

def parse_review_dom(html: str, product_name: str, page: int, total_review_count: str) -> List[Dict]:
    soup = BeautifulSoup(html, "lxml")
    reviews = soup.select("ul#gdasList > li")
    parsed_reviews = []

    for review in reviews:
        try:
            star = review.select_one(".score_area .point").text.strip()
            review_text = review.select_one(".txt_inner").text.strip()
            skin_type_tag = review.select("p.tag span")
            skin_type = skin_type_tag[0].text.strip() if skin_type_tag else "N/A"

            date_tag = review.select_one(".score_area .date")
            date = date_tag.text.strip() if date_tag else "N/A"

            offline_tag = review.select_one(".ico_offlineStore")
            purchase_type = "매장" if offline_tag else "온라인"

            helpful_tag = review.select_one(".recom_area span.num")
            helpful = helpful_tag.text.strip() if helpful_tag else "0"

            parsed_reviews.append({
                "product_name": product_name,
                "star": star,
                "review": review_text,
                "skin_type": skin_type,
                "date": date,
                "purchase_type": purchase_type,
                "page": page,
                "helpful": helpful,
                "total_review_count": total_review_count
            })
        except Exception as e:
            print(f"리뷰 파싱 중 오류 발생: {e}")
            continue

    return parsed_reviews

def crawl_first_page(url: str):
    options = ChromeOptions()
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = Chrome(options=options)

    try:
        print(f"페이지 로드 중: {url}")
        driver.get(url)
        time.sleep(5)

        # 리뷰 탭 클릭
        try:
            review_tab = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//a[contains(@class, "goods_reputation")]'))
            )
            driver.execute_script("arguments[0].click();", review_tab)
            print("리뷰 탭 클릭 완료")
            time.sleep(5)
        except Exception as e:
            print(f"리뷰 탭 클릭 실패: {e}")
            return []

        # 상품 이름 추출
        soup = BeautifulSoup(driver.page_source, 'lxml')
        product_name_tag = soup.find("p", class_="prd_name")
        product_name = product_name_tag.text.strip() if product_name_tag else "N/A"

        # 총 리뷰수 추출
        total_review_count = extract_total_review_count(soup)
        print(f"총 리뷰수: {total_review_count}")

        # 리뷰 파싱
        reviews = parse_review_dom(driver.page_source, product_name, page=1, total_review_count=total_review_count)

        if reviews:
            write_data(reviews)
            print(f"{len(reviews)}개의 리뷰를 저장했습니다.")
        else:
            print("리뷰 없음")

        return reviews

    except Exception as e:
        print(f"크롤링 중 오류 발생: {e}")
        return []

    finally:
        driver.quit()

if __name__ == "__main__":
    url = "https://www.oliveyoung.co.kr/store/goods/getGoodsDetail.do?goodsNo=A000000170266"
    reviews = crawl_first_page(url)
    if reviews:
        print("1페이지 리뷰 크롤링 완료")
    else:
        print("크롤링 실패")
