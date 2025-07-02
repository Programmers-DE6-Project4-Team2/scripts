import time
import json
import csv
from datetime import datetime
from typing import List, Dict, Optional
import pandas as pd
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from fake_useragent import UserAgent
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OliveYoungCrawler:
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.driver = None
        self.wait = None
        self.ua = UserAgent()
        self.setup_driver()
        
    def setup_driver(self):
        """Chrome WebDriver 설정"""
        chrome_options = Options()
        
        if self.headless:
            chrome_options.add_argument('--headless')
        
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument(f'--user-agent={self.ua.random}')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
        except Exception as e:
            logger.error(f"Chrome WebDriver 초기화 실패: {e}")
            # 시스템 Chrome 사용 시도
            self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        self.wait = WebDriverWait(self.driver, 10)
        logger.info("Chrome WebDriver 초기화 완료")
    
    def get_page(self, url: str, wait_time: int = 3) -> bool:
        """페이지 로딩"""
        try:
            self.driver.get(url)
            time.sleep(wait_time)
            return True
        except Exception as e:
            logger.error(f"페이지 로딩 실패: {e}")
            return False
    
    def scroll_to_bottom(self, pause_time: float = 1.0):
        """페이지 끝까지 스크롤"""
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        
        while True:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(pause_time)
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
    
    def extract_product_list(self, category_url: str, max_pages: int = 5) -> List[Dict]:
        """상품 목록 추출"""
        products = []
        
        for page in range(1, max_pages + 1):
            url = f"{category_url}&pageIdx={page}"
            logger.info(f"페이지 {page} 크롤링 중...")
            
            if not self.get_page(url):
                continue
                
            try:
                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                
                # 상품 리스트 추출 (올리브영 실제 구조)
                product_items = soup.find_all('div', class_='prd_info')
                
                if not product_items:
                    logger.warning(f"페이지 {page}에서 상품을 찾을 수 없습니다.")
                    continue
                
                for item in product_items:
                    try:
                        product = self.parse_product_item(item)
                        if product:
                            products.append(product)
                    except Exception as e:
                        logger.error(f"상품 파싱 오류: {e}")
                        continue
                        
            except Exception as e:
                logger.error(f"페이지 {page} 파싱 오류: {e}")
                continue
                
            time.sleep(2)  # 요청 간격
        
        logger.info(f"총 {len(products)}개 상품 추출 완료")
        return products
    
    def parse_product_item(self, item) -> Optional[Dict]:
        """개별 상품 정보 파싱"""
        try:
            # 올리브영 실제 HTML 구조에 맞게 수정
            name = item.find('p', class_='tx_name')
            name = name.get_text(strip=True) if name else ""
            
            brand = item.find('span', class_='tx_brand')
            brand = brand.get_text(strip=True) if brand else ""
            
            # 할인가 (tx_cur) 우선, 없으면 정가 (tx_num)
            price_cur = item.find('span', class_='tx_cur')
            if price_cur:
                price_span = price_cur.find('span', class_='tx_num')
                price = price_span.get_text(strip=True) if price_span else ""
            else:
                price_org = item.find('span', class_='tx_org')
                if price_org:
                    price_span = price_org.find('span', class_='tx_num')
                    price = price_span.get_text(strip=True) if price_span else ""
                else:
                    price = ""
            
            # 상품 URL
            link = item.find('a', class_='prd_thumb')
            product_url = link.get('href') if link else ""
            if product_url and not product_url.startswith('http'):
                product_url = f"https://www.oliveyoung.co.kr{product_url}"
            
            # 평점 (point 클래스의 width 속성에서 추출)
            rating_elem = item.find('span', class_='point')
            rating = ""
            if rating_elem and rating_elem.get('style'):
                style = rating_elem.get('style')
                if 'width:' in style:
                    width_str = style.split('width:')[1].split('%')[0].strip()
                    try:
                        rating = f"{float(width_str)/20:.1f}"  # 100% = 5점 만점
                    except:
                        rating = ""
            
            # 리뷰 수 (괄호 안의 숫자)
            review_area = item.find('p', class_='prd_point_area')
            review_count = ""
            if review_area:
                review_text = review_area.get_text()
                if '(' in review_text and ')' in review_text:
                    review_count = review_text.split('(')[1].split(')')[0].strip()
            
            return {
                'name': name,
                'brand': brand,
                'price': price,
                'url': product_url,
                'rating': rating,
                'review_count': review_count,
                'scraped_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"상품 파싱 오류: {e}")
            return None
    
    def extract_product_details(self, product_url: str) -> Optional[Dict]:
        """상품 상세 정보 추출"""
        if not self.get_page(product_url):
            return None
            
        try:
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # 상품 상세 정보 추출 (실제 선택자는 페이지 분석 후 수정 필요)
            details = {
                'description': '',
                'ingredients': '',
                'how_to_use': '',
                'images': []
            }
            
            # 상품 설명
            desc_elem = soup.find('div', class_='detail_info')
            if desc_elem:
                details['description'] = desc_elem.get_text(strip=True)
            
            # 성분 정보
            ingredients_elem = soup.find('div', class_='ingredients')
            if ingredients_elem:
                details['ingredients'] = ingredients_elem.get_text(strip=True)
            
            # 사용방법
            usage_elem = soup.find('div', class_='usage')
            if usage_elem:
                details['how_to_use'] = usage_elem.get_text(strip=True)
            
            # 이미지
            img_elements = soup.find_all('img', class_='prd_img')
            for img in img_elements:
                src = img.get('src')
                if src:
                    details['images'].append(src)
            
            return details
            
        except Exception as e:
            logger.error(f"상품 상세 정보 추출 오류: {e}")
            return None
    
    def extract_reviews(self, product_url: str, max_reviews: int = 100) -> List[Dict]:
        """리뷰 데이터 추출"""
        reviews = []
        
        if not self.get_page(product_url):
            return reviews
        
        try:
            # 올리브영 리뷰 탭 클릭 
            review_tab = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "a.goods_reputation"))
            )
            review_tab.click()
            time.sleep(3)
            
            # 리뷰 로딩을 위해 스크롤
            self.scroll_to_bottom(1.0)
            
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            review_items = soup.find_all('div', class_='review_item')
            
            for item in review_items[:max_reviews]:
                try:
                    review = self.parse_review_item(item)
                    if review:
                        reviews.append(review)
                except Exception as e:
                    logger.error(f"리뷰 파싱 오류: {e}")
                    continue
            
            logger.info(f"{len(reviews)}개 리뷰 추출 완료")
            
        except Exception as e:
            logger.error(f"리뷰 추출 오류: {e}")
        
        return reviews
    
    def parse_review_item(self, item) -> Optional[Dict]:
        """개별 리뷰 정보 파싱"""
        try:
            # 실제 HTML 구조에 맞게 선택자 수정 필요
            rating = item.find('span', class_='rating')
            rating = rating.get_text(strip=True) if rating else ""
            
            content = item.find('div', class_='review_cont')
            content = content.get_text(strip=True) if content else ""
            
            author = item.find('span', class_='reviewer')
            author = author.get_text(strip=True) if author else ""
            
            date = item.find('span', class_='date')
            date = date.get_text(strip=True) if date else ""
            
            return {
                'rating': rating,
                'content': content,
                'author': author,
                'date': date,
                'scraped_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"리뷰 파싱 오류: {e}")
            return None
    
    def save_to_csv(self, data: List[Dict], filename: str):
        """CSV로 데이터 저장"""
        if not data:
            logger.warning("저장할 데이터가 없습니다.")
            return
            
        df = pd.DataFrame(data)
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        logger.info(f"데이터가 {filename}에 저장되었습니다.")
    
    def save_to_json(self, data: List[Dict], filename: str):
        """JSON으로 데이터 저장"""
        if not data:
            logger.warning("저장할 데이터가 없습니다.")
            return
            
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"데이터가 {filename}에 저장되었습니다.")
    
    def close(self):
        """브라우저 종료"""
        if self.driver:
            self.driver.quit()
            logger.info("브라우저가 종료되었습니다.")