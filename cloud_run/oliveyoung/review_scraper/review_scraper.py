"""
올리브영 리뷰 크롤러 클래스
동작하는 파일(olive0/src/review_scraper.py)을 기반으로 Cloud Run 환경에 최적화
"""

import time
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from undetected_chromedriver import Chrome, ChromeOptions

logger = logging.getLogger(__name__)

class OliveYoungReviewScraper:
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.driver = None
        self.wait = None
        self.setup_driver()
        
    def setup_driver(self):
        """Chrome WebDriver 설정 - oliveyoung_product_scraper.py 참고"""
        options = ChromeOptions()
        
        # Headless 모드 설정
        if self.headless:
            options.add_argument('--headless=new')
        
        # 기본 Chrome 설정
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-infobars')
        
        # User-Agent 설정
        from fake_useragent import UserAgent
        ua = UserAgent()
        options.add_argument(f'--user-agent={ua.random}')
        
        try:
            self.driver = Chrome(options=options)
            # WebDriver 속성 숨기기 
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.wait = WebDriverWait(self.driver, 10)
            logger.info("Chrome WebDriver 초기화 완료 (headless 모드)")
        except Exception as e:
            logger.error(f"Chrome WebDriver 초기화 실패: {e}")
            raise
    
    def get_page(self, url: str, wait_time: int = 5) -> bool:
        """페이지 로딩"""
        try:
            logger.info(f"Loading page: {url}")
            self.driver.get(url)
            time.sleep(wait_time)
            return True
        except Exception as e:
            logger.error(f"페이지 로딩 실패: {e}")
            return False
    
    def extract_reviews(self, product_url: str, max_reviews: int = 100) -> List[Dict]:
        """리뷰 데이터 추출 - 1페이지만 추출"""
        return self.extract_reviews_with_pagination(product_url, max_pages=1)
    
    def extract_reviews_with_pagination(self, product_url: str, max_pages: int = 5) -> List[Dict]:
        """5페이지 제한 리뷰 데이터 추출 - 동작하는 파일 구조 기반"""
        reviews = []
        
        try:
            logger.info(f"페이지 로드 중: {product_url}")
            self.driver.get(product_url)
            time.sleep(5)
            
            # 리뷰 탭 클릭 - 동작하는 파일의 로직 사용
            try:
                review_tab = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, '//a[contains(@class, "goods_reputation")]'))
                )
                self.driver.execute_script("arguments[0].click();", review_tab)
                logger.info("리뷰 탭 클릭 완료")
                time.sleep(5)
            except Exception as e:
                logger.error(f"리뷰 탭 클릭 실패: {e}")
                return reviews
            
            # 상품명 추출 - 동작하는 파일의 로직 사용
            soup = BeautifulSoup(self.driver.page_source, 'lxml')
            product_name_tag = soup.find("p", class_="prd_name")
            product_name = product_name_tag.text.strip() if product_name_tag else "N/A"
            logger.info(f"Product name: {product_name}")
            
            # 각 페이지별 리뷰 수집
            for page in range(1, max_pages + 1):
                logger.info(f"페이지 {page} 리뷰 수집 시작")
                
                # 현재 페이지의 리뷰 파싱
                current_reviews = self.parse_review_dom(self.driver.page_source, product_name, page=page)
                
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
        
        return reviews
    
    
    def go_to_next_page(self, current_page: int) -> bool:
        """다음 페이지로 이동 - 단순화된 로직"""
        try:
            next_page_num = current_page + 1
            
            # 페이지 번호 직접 클릭 시도
            try:
                page_button = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, f"//a[contains(@class, 'num') and text()='{next_page_num}']"))
                )
                self.driver.execute_script("arguments[0].click();", page_button)
                logger.info(f"페이지 {next_page_num} 버튼 클릭 성공")
                time.sleep(5)
                return True
            except:
                logger.warning(f"페이지 {next_page_num} 버튼을 찾을 수 없습니다")
            
            # 다음 버튼 클릭 시도
            try:
                next_button = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//a[contains(@class, 'next')]"))
                )
                self.driver.execute_script("arguments[0].click();", next_button)
                logger.info("다음 버튼 클릭 성공")
                time.sleep(5)
                return True
            except:
                logger.warning("다음 버튼을 찾을 수 없습니다")
            
            logger.warning(f"페이지 {next_page_num}로 이동할 수 없습니다")
            return False
            
        except Exception as e:
            logger.error(f"다음 페이지로 이동 중 오류: {e}")
            return False
    
    def parse_review_dom(self, html: str, product_name: str, page: int) -> List[Dict]:
        """HTML에서 리뷰 파싱 - 동작하는 파일의 검증된 선택자 사용"""
        soup = BeautifulSoup(html, "lxml")
        
        # 동작하는 파일의 검증된 선택자 사용
        reviews_elements = soup.select("ul#gdasList > li")
        
        if not reviews_elements:
            logger.warning("리뷰 요소를 찾을 수 없습니다.")
            return []
        
        logger.info(f"리뷰 요소 {len(reviews_elements)}개 발견")
        parsed_reviews = []
        
        for idx, review in enumerate(reviews_elements):
            try:
                # 평점 추출 - 동작하는 파일의 선택자 사용
                star_elem = review.select_one(".score_area .point")
                star = star_elem.text.strip() if star_elem else "N/A"
                
                # 리뷰 텍스트 추출 - 동작하는 파일의 선택자 사용
                review_text_elem = review.select_one(".txt_inner")
                review_text = review_text_elem.text.strip() if review_text_elem else "N/A"
                
                # 스킨타입 추출 - 동작하는 파일의 선택자 사용
                skin_type_tags = review.select("p.tag span")
                skin_type = skin_type_tags[0].text.strip() if skin_type_tags else "N/A"
                
                # 날짜 추출 - 동작하는 파일의 선택자 사용
                date_elem = review.select_one(".score_area .date")
                date = date_elem.text.strip() if date_elem else "N/A"
                
                # 구매 타입 (온라인/매장) - 동작하는 파일의 로직 사용
                offline_tag = review.select_one(".ico_offlineStore")
                purchase_type = "매장" if offline_tag else "온라인"
                
                # 도움됨 수 - 동작하는 파일의 선택자 사용
                helpful_elem = review.select_one(".recom_area span.num")
                helpful = helpful_elem.text.strip() if helpful_elem else "0"
                
                # 리뷰 ID 생성
                review_id = f"{product_name}_{page}_{idx+1}"
                
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
                    "scraped_at": datetime.now().isoformat()
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
