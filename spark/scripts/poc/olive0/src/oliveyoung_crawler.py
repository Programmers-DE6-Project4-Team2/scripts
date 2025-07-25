import time
import json
import csv
from datetime import datetime
from typing import List, Dict, Optional
import pandas as pd
import requests
from bs4 import BeautifulSoup
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from fake_useragent import UserAgent
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OliveYoungCrawler:
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.driver = None
        self.wait = None
        self.setup_driver()

    def setup_driver(self):
        options = uc.ChromeOptions()

        if self.headless:
            options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-infobars')

        ua = UserAgent()
        options.add_argument(f'--user-agent={ua.random}')

        try:
            self.driver = uc.Chrome(options=options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.wait = WebDriverWait(self.driver, 10)
            logger.info("Chrome WebDriver 초기화 완료 (undetected_chromedriver)")
        except Exception as e:
            logger.error(f"Chrome WebDriver 초기화 실패: {e}")

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

    def get_total_products_from_page(self, category_url: str) -> int:
        """첫 페이지에서 전체 상품 수를 파싱하여 반환"""
        if not self.get_page(category_url):
            return 24  # 기본값
        
        try:
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # <p class="cate_info_tx"> 태그에서 상품 수 추출
            cate_info = soup.find('p', class_='cate_info_tx')
            if cate_info:
                text = cate_info.get_text(strip=True)
                logger.info(f"카테고리 정보: {text}")
                
                # "총 385개" 형태에서 숫자 추출
                import re
                numbers = re.findall(r'\d+', text)
                if numbers:
                    total_count = int(numbers[0])
                    logger.info(f"전체 상품 수: {total_count}개")
                    return total_count
            
            # 다른 방법으로 페이지 정보 찾기
            paging_info = soup.find('div', class_='pageing')
            if paging_info:
                # 페이징 정보에서 총 페이지 수 추출
                page_links = paging_info.find_all('a')
                if page_links:
                    # 마지막 페이지 번호 찾기
                    last_page = 1
                    for link in page_links:
                        try:
                            page_num = int(link.get_text(strip=True))
                            last_page = max(last_page, page_num)
                        except ValueError:
                            continue
                    
                    # 페이지당 24개 상품으로 추정
                    estimated_total = last_page * 24
                    logger.info(f"페이징 정보로부터 추정 상품 수: {estimated_total}개 ({last_page} 페이지)")
                    return estimated_total
            
            return 24  # 기본값
            
        except Exception as e:
            logger.error(f"전체 상품 수 파싱 오류: {e}")
            return 24  # 기본값

    def extract_product_list(self, category_url: str, max_pages: int = None) -> List[Dict]:
        """상품 목록 추출 - 동적 페이지 계산"""
        products = []
        
        # 전체 상품 수 가져오기
        total_products = self.get_total_products_from_page(category_url)
        products_per_page = 24  # 올리브영 기본값
        
        # 총 페이지 수 계산
        if max_pages is None:
            total_pages = (total_products + products_per_page - 1) // products_per_page
        else:
            total_pages = min(max_pages, (total_products + products_per_page - 1) // products_per_page)
        
        logger.info(f"총 {total_products}개 상품, {total_pages}페이지 크롤링 시작")

        for page in range(1, total_pages + 1):
            url = f"{category_url}&pageIdx={page}"
            logger.info(f"페이지 {page}/{total_pages} 크롤링 중...")

            if not self.get_page(url):
                continue

            try:
                soup = BeautifulSoup(self.driver.page_source, 'html.parser')

                # 상품 리스트 추출 (올리브영 실제 구조 - 여러 선택자 시도)
                product_items = soup.find_all('div', class_='prd_info')
                
                # 대안 선택자들 시도
                if not product_items:
                    alternative_selectors = [
                        ('li', 'prd_item'),
                        ('div', 'item'),
                        ('div', 'product'),
                        ('li', 'item'),
                        ('article', None),
                        ('div', 'goods-list-item'),
                    ]
                    
                    for tag, class_name in alternative_selectors:
                        if class_name:
                            product_items = soup.find_all(tag, class_=class_name)
                        else:
                            product_items = soup.find_all(tag)
                            # article 태그 중에서 상품정보가 있는 것들만 필터링
                            if tag == 'article':
                                product_items = [item for item in product_items if item.find('p')]
                        
                        if product_items:
                            logger.info(f"대안 선택자로 상품 발견: {tag}.{class_name} ({len(product_items)}개)")
                            break

                if not product_items:
                    logger.warning(f"페이지 {page}에서 상품을 찾을 수 없습니다.")
                    
                    # 디버깅: 페이지 내용 일부 확인
                    if page <= 2:  # 처음 2페이지만 디버깅
                        logger.info("디버깅: 페이지 구조 분석...")
                        
                        # CloudFlare 감지
                        if "Just a moment" in self.driver.page_source or "Checking your browser" in self.driver.page_source:
                            logger.error("CloudFlare 감지됨 - 봇 차단 상태")
                            
                        # 일반적인 상품 관련 태그들 찾기
                        all_divs = soup.find_all('div', limit=50)
                        div_classes = [div.get('class') for div in all_divs if div.get('class')]
                        logger.info(f"페이지의 div 클래스들: {div_classes[:10]}")
                        
                        # prd 관련 클래스 찾기
                        prd_elements = soup.find_all(class_=lambda x: x and any('prd' in cls.lower() for cls in x))
                        logger.info(f"'prd' 포함 클래스 {len(prd_elements)}개 발견")
                        for elem in prd_elements[:3]:
                            logger.info(f"  {elem.name}.{elem.get('class')}")
                    
                    # 연속으로 3페이지 이상 빈 페이지가 나오면 중단
                    if page > 3:
                        empty_pages = 0
                        for check_page in range(max(1, page-2), page+1):
                            if check_page == page:
                                empty_pages += 1
                        if empty_pages >= 3:
                            logger.info("연속 빈 페이지 감지, 크롤링 중단")
                            break
                    continue

                page_products = []
                for item in product_items:
                    try:
                        product = self.parse_product_item(item)
                        if product:
                            page_products.append(product)
                    except Exception as e:
                        logger.error(f"상품 파싱 오류: {e}")
                        continue

                products.extend(page_products)
                logger.info(f"페이지 {page}: {len(page_products)}개 상품 수집 (총 {len(products)}개)")

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
            
            # 상품 ID 추출 (URL에서 추출)
            product_id = ""
            if product_url:
                # URL 패턴: /goods/getGoodsDetail.do?goodsNo=A000000211137
                import re
                match = re.search(r'goodsNo=([A-Z0-9]+)', product_url)
                if match:
                    product_id = match.group(1)

            # 평점 (point 클래스의 width 속성에서 추출)
            rating_elem = item.find('span', class_='point')
            rating = ""
            if rating_elem and rating_elem.get('style'):
                style = rating_elem.get('style')
                if 'width:' in style:
                    width_str = style.split('width:')[1].split('%')[0].strip()
                    try:
                        rating = f"{float(width_str) / 20:.1f}"  # 100% = 5점 만점
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
                'product_id': product_id,
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
        """리뷰 데이터 추출 - 실제 올리브영 구조에 맞춰 수정"""
        reviews = []

        if not self.get_page(product_url):
            return reviews

        try:
            # 올리브영 리뷰 탭 찾기 시도 (여러 선택자 시도)
            review_tab_selectors = [
                "a.goods_reputation",
                "a[href*='review']",
                "//a[contains(text(), '리뷰')]"
            ]

            review_tab = None
            for selector in review_tab_selectors:
                try:
                    if selector.startswith("//"):
                        # XPath 사용
                        review_tab = self.wait.until(
                            EC.element_to_be_clickable((By.XPATH, selector))
                        )
                    else:
                        # CSS 선택자 사용
                        review_tab = self.wait.until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                        )
                    logger.info(f"리뷰 탭 발견: {selector}")
                    break
                except:
                    continue

            if not review_tab:
                logger.warning("리뷰 탭을 찾을 수 없습니다.")
                return reviews

            # 리뷰 탭 클릭
            self.driver.execute_script("arguments[0].click();", review_tab)
            time.sleep(10)  # 리뷰 로딩 대기 시간 증가

            # 리뷰 더보기 버튼 클릭으로 더 많은 리뷰 로드
            self.load_more_reviews(max_reviews)

            # 페이지 소스 다시 파싱
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')

            # 실제 리뷰 컨테이너 찾기 - 올리브영 특화
            review_container_selectors = [
                '.prd_social_info',  # 발견된 클래스
                '.review_wrap',
                '.review_list',
                '.prd_review_wrap',
                'ul',  # 일반적인 리스트
                '.goods_review',
                '[class*="review"]'
            ]

            review_items = []
            for selector in review_container_selectors:
                container = soup.select_one(selector)
                if container:
                    # 개별 리뷰 항목들 찾기
                    items = container.find_all(['div', 'li'], class_=lambda x: x and
                                                                               any(keyword in ' '.join(x).lower()
                                                                                   for keyword in
                                                                                   ['review', 'comment', 'item']))
                    if items:
                        review_items = items
                        logger.info(f"리뷰 컨테이너 발견: {selector}, {len(items)}개 리뷰")
                        break

            if not review_items:
                logger.warning("리뷰 항목을 찾을 수 없습니다.")

                # 디버그: 리뷰 섹션 HTML 구조 확인
                logger.info("디버그: 리뷰 섹션 HTML 구조 분석...")

                # 모든 가능한 리뷰 관련 요소들 찾기
                all_review_elements = soup.find_all(string=lambda text: text and '리뷰' in text)
                logger.info(f"'리뷰' 텍스트가 포함된 요소 {len(all_review_elements)}개 발견")

                # 리뷰 텍스트를 포함한 요소들의 부모 찾기
                for i, text_elem in enumerate(all_review_elements[:3]):
                    parent = text_elem.parent if hasattr(text_elem, 'parent') else None
                    if parent:
                        logger.info(f"  리뷰 텍스트 {i + 1}: '{text_elem.strip()[:30]}...'")
                        logger.info(f"    부모 태그: {parent.name}, class: {parent.get('class')}")

                        # 부모의 부모도 확인
                        grandparent = parent.parent if parent.parent else None
                        if grandparent:
                            logger.info(f"    조부모 태그: {grandparent.name}, class: {grandparent.get('class')}")

                # class에 review가 포함된 모든 요소 찾기
                review_class_elements = soup.find_all(class_=lambda x: x and any('review' in cls.lower() for cls in x))
                logger.info(f"class에 'review'가 포함된 요소 {len(review_class_elements)}개 발견")

                # li 태그들 중에서 리뷰일 가능성이 있는 것들 찾기
                all_li_elements = soup.find_all('li')
                logger.info(f"전체 li 태그 {len(all_li_elements)}개 발견")

                # li 태그 중에서 텍스트가 긴 것들 (리뷰일 가능성)
                content_li_elements = [li for li in all_li_elements if
                                       li.get_text(strip=True) and len(li.get_text(strip=True)) > 30]
                logger.info(f"내용이 있는 li 태그 {len(content_li_elements)}개 발견")

                for i, li in enumerate(content_li_elements[:3]):
                    logger.info(f"  li {i + 1}: class={li.get('class')}, 텍스트='{li.get_text(strip=True)[:50]}...'")

                # 만약 내용이 있는 li가 있다면 리뷰로 간주하고 파싱 시도
                if content_li_elements:
                    logger.info("li 태그들을 리뷰 항목으로 간주하고 파싱 시도...")
                    for idx, li in enumerate(content_li_elements[:max_reviews]):
                        try:
                            review = self.parse_review_item(li, idx + 1)
                            if review:
                                reviews.append(review)
                        except Exception as e:
                            logger.error(f"li 리뷰 {idx + 1} 파싱 오류: {e}")
                            continue

                    if reviews:
                        logger.info(f"li 태그에서 {len(reviews)}개 리뷰 추출 성공!")
                        return reviews

                # div 태그들 중에서 내용이 긴 것들 찾기 (리뷰일 가능성)
                content_divs = soup.find_all('div', string=lambda text: text and len(text.strip()) > 20)
                logger.info(f"긴 텍스트가 있는 div {len(content_divs)}개 발견")

                # 평점 관련 요소들 찾기
                rating_elements = soup.find_all(['span', 'div'], class_=lambda x: x and any(
                    keyword in ' '.join(x).lower() for keyword in ['star', 'point', 'score', '별']))
                logger.info(f"평점 관련 요소 {len(rating_elements)}개 발견")

                # 실제 사용자 리뷰 내용으로 보이는 패턴 찾기
                potential_reviews = soup.find_all(string=lambda text: text and len(text.strip()) > 50 and any(
                    keyword in text for keyword in ['좋아요', '만족', '추천', '괜찮', '별로']))
                logger.info(f"리뷰 내용으로 보이는 텍스트 {len(potential_reviews)}개 발견")

                for i, review_text in enumerate(potential_reviews[:2]):
                    logger.info(f"  잠재 리뷰 {i + 1}: '{review_text.strip()[:50]}...'")
                    parent = review_text.parent if hasattr(review_text, 'parent') else None
                    if parent:
                        logger.info(f"    부모: {parent.name}, class: {parent.get('class')}")

                return reviews

            # 각 리뷰 항목 파싱
            for idx, item in enumerate(review_items[:max_reviews]):
                try:
                    review = self.parse_review_item(item, idx + 1)
                    if review:
                        reviews.append(review)
                except Exception as e:
                    logger.error(f"리뷰 {idx + 1} 파싱 오류: {e}")
                    continue

            logger.info(f"{len(reviews)}개 리뷰 추출 완료")

        except Exception as e:
            logger.error(f"리뷰 추출 오류: {e}")

        return reviews

    def load_more_reviews(self, max_reviews: int):
        """리뷰 더보기 버튼 클릭으로 더 많은 리뷰 로드"""
        try:
            # 더보기 버튼 선택자들
            more_button_selectors = [
                ".btn_more",
                ".more_btn",
                "button[class*='more']",
                "a[class*='more']",
                "//button[contains(text(), '더보기')]",
                "//a[contains(text(), '더보기')]"
            ]

            loaded_count = 0
            max_attempts = 10  # 최대 10번 더보기 시도

            for attempt in range(max_attempts):
                more_button = None

                # 더보기 버튼 찾기
                for selector in more_button_selectors:
                    try:
                        if selector.startswith("//"):
                            more_button = self.driver.find_element(By.XPATH, selector)
                        else:
                            more_button = self.driver.find_element(By.CSS_SELECTOR, selector)

                        if more_button and more_button.is_displayed():
                            break
                    except:
                        continue

                if not more_button:
                    logger.info("더보기 버튼을 찾을 수 없습니다.")
                    break

                try:
                    # 더보기 버튼 클릭
                    self.driver.execute_script("arguments[0].click();", more_button)
                    time.sleep(2)
                    loaded_count += 1
                    logger.info(f"더보기 버튼 클릭 {loaded_count}회")

                    # 현재 로드된 리뷰 수 확인
                    current_reviews = len(self.driver.find_elements(By.CSS_SELECTOR, "[class*='review']"))
                    if current_reviews >= max_reviews:
                        logger.info(f"목표 리뷰 수 {max_reviews}개 달성")
                        break

                except Exception as e:
                    logger.warning(f"더보기 버튼 클릭 실패: {e}")
                    break

        except Exception as e:
            logger.error(f"리뷰 더 로드 중 오류: {e}")

    def parse_review_item(self, item, review_number: int = 0) -> Optional[Dict]:
        """개별 리뷰 정보 파싱 - 실제 올리브영 구조에 맞춰 수정"""
        try:
            review_data = {
                'review_number': review_number,
                'rating': '',
                'title': '',
                'content': '',
                'author': '',
                'date': '',
                'helpful_count': '',
                'scraped_at': datetime.now().isoformat()
            }

            # 평점 추출 (여러 방식 시도)
            rating_selectors = [
                'span[class*="rating"]',
                'span[class*="star"]',
                'span[class*="score"]',
                'span[class*="point"]',
                'div[class*="rating"]'
            ]

            for selector in rating_selectors:
                rating_elem = item.select_one(selector)
                if rating_elem:
                    # 텍스트에서 평점 추출
                    rating_text = rating_elem.get_text(strip=True)
                    if rating_text:
                        review_data['rating'] = rating_text
                        break

                    # style 속성에서 width 값으로 평점 계산
                    style = rating_elem.get('style', '')
                    if 'width:' in style:
                        try:
                            width_str = style.split('width:')[1].split('%')[0].strip()
                            rating_value = f"{float(width_str) / 20:.1f}"  # 100% = 5점
                            review_data['rating'] = rating_value
                            break
                        except:
                            continue

            # 리뷰 제목 추출
            title_selectors = [
                'h3[class*="title"]',
                'div[class*="title"]',
                'span[class*="title"]',
                'p[class*="title"]'
            ]

            for selector in title_selectors:
                title_elem = item.select_one(selector)
                if title_elem:
                    review_data['title'] = title_elem.get_text(strip=True)
                    break

            # 리뷰 내용 추출
            content_selectors = [
                'div[class*="content"]',
                'div[class*="comment"]',
                'p[class*="content"]',
                'span[class*="content"]',
                'div[class*="text"]',
                'p[class*="review"]'
            ]

            for selector in content_selectors:
                content_elem = item.select_one(selector)
                if content_elem:
                    content = content_elem.get_text(strip=True)
                    if len(content) > 10:  # 실제 리뷰 내용일 가능성이 높은 긴 텍스트만
                        review_data['content'] = content
                        break

            # 작성자 추출
            author_selectors = [
                'span[class*="author"]',
                'span[class*="user"]',
                'span[class*="name"]',
                'span[class*="writer"]',
                'div[class*="user"]'
            ]

            for selector in author_selectors:
                author_elem = item.select_one(selector)
                if author_elem:
                    author_text = author_elem.get_text(strip=True)
                    if author_text and not any(word in author_text.lower() for word in ['평점', 'rating', '별점']):
                        review_data['author'] = author_text
                        break

            # 작성일 추출
            date_selectors = [
                'span[class*="date"]',
                'span[class*="time"]',
                'div[class*="date"]',
                'p[class*="date"]'
            ]

            for selector in date_selectors:
                date_elem = item.select_one(selector)
                if date_elem:
                    date_text = date_elem.get_text(strip=True)
                    # 날짜 패턴이 있는지 확인 (예: 2024-07-02, 2024.07.02 등)
                    if any(char.isdigit() for char in date_text) and len(date_text) >= 8:
                        review_data['date'] = date_text
                        break

            # 도움됨 수 추출
            helpful_selectors = [
                'span[class*="helpful"]',
                'span[class*="like"]',
                'button[class*="helpful"]',
                'span[class*="recommend"]'
            ]

            for selector in helpful_selectors:
                helpful_elem = item.select_one(selector)
                if helpful_elem:
                    helpful_text = helpful_elem.get_text(strip=True)
                    if helpful_text and any(char.isdigit() for char in helpful_text):
                        review_data['helpful_count'] = helpful_text
                        break

            # 최소한 내용이나 평점이 있어야 유효한 리뷰로 간주
            if review_data['content'] or review_data['rating']:
                return review_data
            else:
                return None

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

    def save_reviews_to_csv(self, reviews: List[Dict], filename: str):
        """리뷰 데이터 CSV 저장"""
        if not reviews:
            logger.warning("저장할 리뷰 데이터가 없습니다.")
            return

        df = pd.DataFrame(reviews)
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        logger.info(f"리뷰 데이터가 {filename}에 저장되었습니다.")

    def save_reviews_to_json(self, reviews: List[Dict], filename: str):
        """리뷰 데이터 JSON 저장"""
        if not reviews:
            logger.warning("저장할 리뷰 데이터가 없습니다.")
            return

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(reviews, f, ensure_ascii=False, indent=2)
        logger.info(f"리뷰 데이터가 {filename}에 저장되었습니다.")

    def close(self):
        """브라우저 종료"""
        if self.driver:
            self.driver.quit()
            logger.info("브라우저가 종료되었습니다.")
