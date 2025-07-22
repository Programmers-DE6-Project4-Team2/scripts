"""
올리브영 리뷰 크롤러 모듈
oliveyoung_product_crawler.py의 Chrome 설정을 참고하여 최적화
"""

import time
import logging
import re
from datetime import datetime, timezone
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from undetected_chromedriver import Chrome, ChromeOptions
from fake_useragent import UserAgent

logger = logging.getLogger(__name__)

class OliveYoungReviewCrawler:
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.driver = None
        self.wait = None
        self.setup_driver()
        
    def setup_driver(self):
        """Chrome WebDriver 설정 - oliveyoung_product_crawler.py 참고"""
        options = ChromeOptions()
        
        # Headless 모드 설정
        if self.headless:
            options.add_argument('--headless=new')
        
        # 기본 Chrome 설정 (oliveyoung_product_crawler.py 참고)
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-infobars')
        
        # User-Agent 설정 (fake_useragent 사용)
        ua = UserAgent()
        options.add_argument(f'--user-agent={ua.random}')
        
        try:
            self.driver = Chrome(options=options)
            # WebDriver 속성 숨기기 (oliveyoung_product_crawler.py 참고)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.wait = WebDriverWait(self.driver, 10)
            logger.info("Chrome WebDriver 초기화 완료 (headless 모드)")
        except Exception as e:
            logger.error(f"Chrome WebDriver 초기화 실패: {e}")
            raise
    
    def get_page(self, url: str, wait_time: int = 5) -> bool:
        """페이지 로딩"""
        try:
            logger.info(f"페이지 로드 중: {url}")
            self.driver.get(url)
            time.sleep(wait_time)
            return True
        except Exception as e:
            logger.error(f"페이지 로딩 실패: {e}")
            return False
    
    def extract_total_review_count(self, soup: BeautifulSoup) -> str:
        """리뷰 탭에서 총 리뷰 수 추출"""
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
            logger.error(f"총 리뷰수 추출 중 오류 발생: {e}")
            return "N/A"
    
    def extract_reviews_with_pagination(self, product_url: str, max_pages: int = 5) -> tuple[List[Dict], str]:
        """리뷰 데이터 추출 with 페이지네이션 - 카테고리 정보도 함께 반환"""
        reviews = []
        category_name = "N/A"
        
        try:
            logger.info(f"페이지 로드 중: {product_url}")
            self.driver.get(product_url)
            time.sleep(8)  # 페이지 로드 대기 시간 증가
            
            # 메인 페이지에서 카테고리 정보 먼저 추출
            soup = BeautifulSoup(self.driver.page_source, 'lxml')
            
            # 카테고리 정보 추출 (page_location에서)
            category_name = "N/A"
            page_location = soup.find("div", class_="page_location")
            if page_location:
                categories = []
                # 홈 링크 제외하고 카테고리 링크들 찾기
                category_links = page_location.find_all("a", class_="cate_y")
                for link in category_links:
                    category_text = link.text.strip()
                    if category_text:
                        categories.append(category_text)
                
                if categories:
                    # 첫번째_두번째&세번째 형태로 파싱
                    if len(categories) == 1:
                        category_name = categories[0]
                    elif len(categories) == 2:
                        category_name = f"{categories[0]}_{categories[1]}"
                    else:
                        # 3개 이상일 때: 첫번째_두번째&세번째&네번째...
                        first_category = categories[0]
                        rest_categories = "&".join(categories[1:])
                        category_name = f"{first_category}_{rest_categories}"
            
            logger.info(f"카테고리 추출: {category_name}")
            
            # 리뷰 탭 클릭
            try:
                review_tab = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, '//a[contains(@class, "goods_reputation")]'))
                )
                self.driver.execute_script("arguments[0].click();", review_tab)
                logger.info("리뷰 탭 클릭 완료")
                time.sleep(8)  # 리뷰 탭 클릭 후 대기 시간 증가
            except Exception as e:
                logger.error(f"리뷰 탭 클릭 실패: {e}")
                return reviews, category_name
            
            # 상품명 추출
            soup = BeautifulSoup(self.driver.page_source, 'lxml')
            product_name_tag = soup.find("p", class_="prd_name")
            product_name = product_name_tag.text.strip() if product_name_tag else "N/A"
            
            # 총 리뷰 수 추출
            total_review_count = self.extract_total_review_count(soup)
            
            logger.info(f"상품명: {product_name}")
            logger.info(f"카테고리: {category_name}")
            logger.info(f"총 리뷰 수: {total_review_count}")
            
            # 각 페이지별 리뷰 수집
            for page in range(1, max_pages + 1):
                logger.info(f"페이지 {page} 리뷰 수집 시작")
                
                # 현재 페이지의 리뷰 파싱
                current_reviews = self.parse_review_dom(self.driver.page_source, product_name, page=page, total_review_count=total_review_count)
                
                if current_reviews:
                    reviews.extend(current_reviews)
                    logger.info(f"페이지 {page}에서 {len(current_reviews)}개 리뷰 수집")
                else:
                    logger.warning(f"페이지 {page}에서 리뷰를 찾을 수 없습니다.")
                
                # 마지막 페이지가 아니면 다음 페이지로 이동
                if page < max_pages:
                    if not self.go_to_next_page(page):
                        logger.info(f"페이지 {page + 1}로 이동 실패 - 더 이상 페이지가 없거나 오류 발생")
                        break
                    
                    # 페이지 로딩 대기
                    time.sleep(3)
            
            logger.info(f"총 {len(reviews)}개 리뷰 추출 완료 (최대 {max_pages}페이지)")
            
        except Exception as e:
            logger.error(f"리뷰 추출 중 오류: {e}")
        
        return reviews, category_name
    
    def go_to_next_page(self, current_page: int) -> bool:
        """다음 페이지로 이동 - data-page-no 속성 기반"""
        try:
            next_page_num = current_page + 1
            
            # data-page-no 속성으로 페이지 번호 직접 클릭 시도
            try:
                page_button = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, f"//a[@data-page-no='{next_page_num}']"))
                )
                self.driver.execute_script("arguments[0].click();", page_button)
                logger.info(f"페이지 {next_page_num} 버튼 클릭 성공 (data-page-no)")
                time.sleep(5)
                return True
            except:
                logger.warning(f"페이지 {next_page_num} 버튼을 찾을 수 없습니다 (data-page-no)")
            
            # 텍스트로 페이지 번호 클릭 시도 (백업)
            try:
                page_button = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, f"//a[text()='{next_page_num}']"))
                )
                self.driver.execute_script("arguments[0].click();", page_button)
                logger.info(f"페이지 {next_page_num} 버튼 클릭 성공 (텍스트)")
                time.sleep(5)
                return True
            except:
                logger.warning(f"페이지 {next_page_num} 버튼을 찾을 수 없습니다 (텍스트)")
            
            # 다음 10페이지 버튼 클릭 시도 (10페이지 경계일 때)
            try:
                next_button = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//a[contains(@class, 'next') and contains(text(), '다음')]"))
                )
                self.driver.execute_script("arguments[0].click();", next_button)
                logger.info("다음 10페이지 버튼 클릭 성공")
                time.sleep(5)
                return True
            except:
                logger.warning("다음 10페이지 버튼을 찾을 수 없습니다")
            
            logger.warning(f"페이지 {next_page_num}로 이동할 수 없습니다")
            return False
            
        except Exception as e:
            logger.error(f"다음 페이지로 이동 중 오류: {e}")
            return False
    
    def parse_review_dom(self, html: str, product_name: str, page: int, total_review_count: str = "N/A") -> List[Dict]:
        """HTML에서 리뷰 파싱"""
        soup = BeautifulSoup(html, "lxml")
        
        # 리뷰 요소 선택
        reviews_elements = soup.select("ul#gdasList > li")
        
        if not reviews_elements:
            logger.warning("리뷰 요소를 찾을 수 없습니다.")
            return []
        
        logger.info(f"리뷰 요소 {len(reviews_elements)}개 발견")
        parsed_reviews = []
        
        for idx, review in enumerate(reviews_elements):
            try:
                # 실제 리뷰 ID 추출 (HTML의 id="gdas_숫자" 형태에서)
                review_id = "N/A"
                btn_recom = review.select_one("button.btn_recom[id^='gdas_']")
                if btn_recom and btn_recom.get('id'):
                    review_id = btn_recom.get('id').replace('gdas_', '')
                
                # 평점 추출
                star_elem = review.select_one(".score_area .point")
                star = star_elem.text.strip() if star_elem else "N/A"
                
                # 리뷰 텍스트 추출
                review_text_elem = review.select_one(".txt_inner")
                review_text = review_text_elem.text.strip() if review_text_elem else "N/A"
                
                # 스킨타입 추출
                skin_type_tags = review.select("p.tag span")
                skin_type = skin_type_tags[0].text.strip() if skin_type_tags else "N/A"
                
                # 날짜 추출
                date_elem = review.select_one(".score_area .date")
                date = date_elem.text.strip() if date_elem else "N/A"
                
                # 구매 타입 (온라인/매장)
                offline_tag = review.select_one(".ico_offlineStore")
                purchase_type = "매장" if offline_tag else "온라인"
                
                # 도움됨 수
                helpful_elem = review.select_one(".recom_area span.num")
                helpful = helpful_elem.text.strip() if helpful_elem else "0"
                
                parsed_review = {
                    "review_id": review_id,
                    "product_name": product_name,
                    "star": star,
                    "review": review_text,
                    "skin_type": skin_type,
                    "date": date,
                    "purchase_type": purchase_type,
                    "page": page,
                    "helpful": helpful,
                    "scraped_at": datetime.now(timezone.utc).isoformat(),
                    "total_review_count": total_review_count
                }
                
                # 최소한 평점이나 리뷰 텍스트가 있어야 유효한 리뷰로 간주
                if star != "N/A" or (review_text != "N/A" and len(review_text) > 5):
                    parsed_reviews.append(parsed_review)
                    
            except Exception as e:
                logger.error(f"리뷰 {idx+1} 파싱 중 오류 발생: {e}")
                continue
        
        logger.info(f"페이지 {page}에서 {len(parsed_reviews)}개 리뷰 파싱 완료")
        return parsed_reviews
    
    def close(self):
        """브라우저 종료"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("브라우저가 종료되었습니다.")
            except Exception as e:
                logger.error(f"브라우저 종료 중 오류: {e}")
