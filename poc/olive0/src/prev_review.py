import time
import csv
import os
from bs4 import BeautifulSoup
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from undetected_chromedriver import Chrome, ChromeOptions
import pandas as pd

def write_data(data):
    file_path = "./data/suncream_reviews_score.csv"
    file_exists = os.path.isfile(file_path)

    with open(file_path, "a", newline='', encoding='utf-8') as fw:
        fieldnames = ["product_name", "star", "title", "review", "skin_type", "page"]
        writer = csv.DictWriter(fw, fieldnames=fieldnames)

        if not file_exists:
            writer.writeheader()

        for row in data:
            writer.writerow(row)

def crawl_parse_review_html_write_data(url):
    # Selenium 설정
    options = ChromeOptions()
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = Chrome(options=options)

    try:
        # 페이지 로드
        print(f"페이지 로드 중: {url}")
        driver.get(url)
        time.sleep(5)  # 초기 로딩 대기

        # 리뷰 탭 클릭
        try:
            review_tab = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//a[contains(@class, "goods_reputation")]'))
            )
            driver.execute_script("arguments[0].click();", review_tab)
            print("리뷰 탭 클릭 완료")
            time.sleep(5)
        except (TimeoutException, NoSuchElementException) as e:
            print(f"리뷰 탭 클릭 실패: {e}")
            return []

        # "더보기" 버튼 반복 클릭
        while True:
            try:
                more_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "a.btn_more, a.next"))
                )
                driver.execute_script("arguments[0].click();", more_button)
                print("더보기 버튼 클릭")
                time.sleep(3)
            except (TimeoutException, NoSuchElementException):
                print("더보기 버튼 없음 또는 모두 로드됨")
                break

        # 페이지 끝까지 스크롤
        for _ in range(5):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            print("페이지 스크롤 중...")
            time.sleep(3)

        # HTML 파싱
        html = driver.page_source
        soup = BeautifulSoup(html, 'lxml')

        # 디버깅: 페이지 소스 저장
        with open("page_source.html", "w", encoding="utf-8") as f:
            f.write(soup.prettify())
        print("페이지 소스를 'page_source.html'로 저장했습니다.")

        # 상품 이름 추출
        product_name_tag = soup.find("p", class_="prd_name")
        product_name = product_name_tag.text.strip() if product_name_tag else "N/A"

        # 리뷰 데이터 추출
        user_clrfix_tags = soup.find_all("div", class_="user clrfix")
        review_tags = soup.find_all("div", class_="txt_inner")
        title_tags = soup.find_all("div", class_="poll_sample")
        star_tags = soup.find_all("div", class_="score_area")

        # 데이터 결합 및 처리
        combined_list = list(zip_longest(title_tags, review_tags, user_clrfix_tags, star_tags, fillvalue=None))
        review_data_list = []
        page_num = 1  # 단일 페이지 내에서 고유 번호

        for title_tag, review_tag, user_clrfix_tag, star_tag in combined_list:
            review_text = review_tag.text.strip() if review_tag else "N/A"
            title_text = [tag.text.strip() for tag in
                         title_tag.find_all("span")[1::2]] if title_tag and title_tag.find_all("span") else ["N/A"]
            span_text = [span.text.strip() for span in
                        user_clrfix_tag.find_all("span")[1:]] if user_clrfix_tag and user_clrfix_tag.find_all(
                "span") else ["N/A"]
            star_text = [star.text.strip() for star in star_tag.find_all("span")][0] if star_tag and star_tag.find_all(
                "span") else "N/A"

            review_data = {
                "product_name": product_name,
                "star": star_text,
                "title": title_text[0] if title_text and title_text[0] != "N/A" else "N/A",
                "review": review_text,
                "skin_type": span_text[0] if span_text and span_text[0] != "N/A" else "N/A",
                "page": page_num
            }
            review_data_list.append(review_data)
            page_num += 1

        # 데이터 저장
        if review_data_list:
            write_data(review_data_list)
            print(f"{len(review_data_list)}개의 리뷰를 저장했습니다.")
        else:
            print("추출된 리뷰가 없습니다.")

        return review_data_list

    except Exception as e:
        print(f"크롤링 중 오류 발생: {e}")
        return []

    finally:
        driver.quit()

if __name__ == "__main__":
    url = "https://www.oliveyoung.co.kr/store/goods/getGoodsDetail.do?goodsNo=A000000170266"
    parse_review_list = crawl_parse_review_html_write_data(url)
    if parse_review_list:
        print("크롤링 완료")
    else:
        print("크롤링 실패")
